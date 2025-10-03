import fetch from 'node-fetch'
import subprocess from 'node:child_process'

import { config, file, help_message, signal, spawn_options } from './constants.mjs'
import { log, setup_logging, status } from './logging.mjs'
import {
    as_num,
    cat,
    join_command,
    overwrite,
    pwsh_command,
    readlines,
    run,
    safe_rm,
    send_signal,
    sleep,
    test_command,
} from './utils.mjs'

/** @param pid {string | number | null} */
const set_pid = pid => {
    if (pid == null) safe_rm(file.pid)
    else overwrite(file.pid, pid?.toString())
}

/** @returns {number | void} */
const get_pid = () => {
    const command = () =>
        (process.platform === 'win32' && pwsh_command('(ps n8n -erroraction silentlycontinue).id'))
        || join_command('string=$(ps -x | grep [n]8n)', 'array=( $string )', 'echo ${array[0]}')

    let pid = cat(file.pid)

    if (!pid) {
        pid = run(command()).output
        set_pid(pid || null)
    }

    return as_num(pid.trim())
}

/** @returns {Promise<[number, boolean] | void>} */
const inspect_state = async () => {
    try {
        const pid = get_pid()
        if (!pid) throw null
        send_signal(pid, 0)
        return [pid, await fetch(`http://localhost:${config.port}/`).then(res => res.ok)]
    } catch {}
}

const state_message = async () => {
    const [pid = null, health = false] = (await inspect_state()) ?? []
    return `server is ${
        pid ?
            health ? 'healthy'
            :   'unresponsive'
        :   'down'
    }`
}

const initialize_handlers = () =>
    ['beforeExit', 'uncaughtException', signal.SIGINT, signal.SIGTERM].forEach(item =>
        process.on(item, () => set_pid(null)),
    )

// -- COMMAND FUNCTIONS -- //
export const show_help = () => console.log(help_message)
export const clean_logs = () => Object.values(file).forEach(safe_rm)

/** @returns {Promise<[number, boolean] | void>} */
export const start_server = async () => {
    setup_logging()

    const state = await inspect_state()
    const [pid, health] = state ?? []
    if (health) {
        log('INFO', `server is already running (pid: ${pid})`)
        return state
    } else if (pid) {
        log('ALERT', `server is running but is unresponsive.`)
        await stop_server()
    }

    log('INFO', 'starting n8n server')

    /** @param name {string} */
    const serve = name => subprocess.spawn(name, ['x', 'n8n'], spawn_options)

    /** @type {import('node:child_process').ChildProcess | null} */
    let proc = null
    if (test_command('bun')) proc = serve('bun')
    else if (test_command('npm')) proc = serve('npm')

    if (!proc?.pid) return log('ERROR', 'no node runtime detected')

    set_pid(proc.pid)
    initialize_handlers()

    return await sleep(5, async () => {
        if (!(await inspect_state())) return log('ERROR', 'n8n server failed to start')
        else {
            log('SUCCESS', 'n8n server started successfully')

            status.alert('waiting for server to be ready...')
            const { restart_delay, startup_timeout } = config.timings

            const max = Math.floor(startup_timeout / restart_delay)

            let ct = 0
            while (ct < max) {
                const current_state = await inspect_state()
                const [pid, health] = current_state ?? []

                if (health) {
                    log('SUCCESS', `server is ready and responding on port ${config.port}`)
                    return current_state
                } else await sleep(3, () => void ct++)

                if (!pid) return log('ERROR', 'server process died during startup')
                else status.alert(`not ready yet (${ct}/${max})`)
            }
            log('ALERT', 'health check failed, but the process is running')
            return inspect_state()
        }
    })
}

/** @returns {Promise<[number, boolean] | void>} */
export const stop_server = async () => {
    const state = await inspect_state()
    if (!state) return status.alert('server is not running')

    log('INFO', `stopping n8n server (pid: ${state[0]})...`)

    const refresh = async () => ((await inspect_state()) ?? [])[0]

    /** @param {boolean} _refresh */
    const try_kill = async (_refresh = false) => {
        const pid = _refresh ? await refresh() : state[0]
        try {
            if (!pid) return
            send_signal(pid, signal.SIGTERM)
            return await sleep(1, refresh)
        } catch {}
    }

    /** @param {number} pid */
    const force_kill = pid => {
        status.alert('graceful shutdown failed; force killing...')
        send_signal(pid, signal.SIGKILL)
    }

    /** @type {number | undefined} */
    let pid

    if (await try_kill()) {
        let ct = 0
        while (ct < 10 && !(pid = await try_kill(true))) await sleep(1, () => void ct++)
        if ((pid = await refresh())) force_kill(pid)
    }

    const final_state = await inspect_state()

    if (final_state) {
        const [pid, health] = final_state
        log('ERROR', `could not kill process (pid: ${pid})`)
        return [pid, health]
    }

    set_pid(null)
    return log('SUCCESS', 'server stopped successfully')
}

/**
 * @param {number} ct
 */
const retry_restart = async ct => {
    const delay = config.timings.restart_delay
    log('ERROR', `restart attempt failed. waiting ${delay} seconds...`)
    return await sleep(delay, async () => await restart_server((ct += 1)))
}

const restart_result = Object.freeze({
    /** @param {[number, boolean]} state */
    ok: state => {
        log('SUCCESS', 'server restarted successfully')
        return state
    },
    /**
     * @param {unknown} err
     * @param {number} ct
     */
    err: async (err, ct) => {
        const message =
            err && typeof err == 'object' && 'message' in err && typeof err.message == 'string' ?
                `${err.message}`
            :   'something went wrong'
        log('ERROR', message)
        return await retry_restart(ct)
    },

    exceed: () => {
        log('ERROR', 'maximum restart attempts exceeded. exiting.')
        return undefined
    },
})

/**
 * @param {number} _ct
 * @returns {Promise<[number, boolean] | undefined>}
 */
export const restart_server = async (_ct = 0) => {
    let [pid = null, health = false] = (await inspect_state()) ?? []

    const info_data = { attempts: `${_ct}/${config.max_restarts}`, status: await state_message() }
    log('INFO', JSON.stringify(info_data, undefined, 4))

    if (_ct >= config.max_restarts && !pid) return restart_result.exceed()
    else if (_ct && pid && health) return restart_result.ok([pid, health])
    else if (pid) await stop_server()

    log('ALERT', `attempting to restart server...`)
    return await sleep(2, async () =>
        start_server().then(async state => (state ? restart_result.ok(state) : await retry_restart(_ct))),
    ).catch(async err => await restart_result.err(err, _ct))
}

export const monitor_server = async () => {
    if (!(await inspect_state())) await start_server()
    log('INFO', 'starting server monitor with auto-restart enabled')
    while (true) {
        const [, health] = (await inspect_state()) ?? []
        let level = 'INFO'
        if (health) level = 'SUCCESS'
        else await restart_server().then(state => !state && (level = 'ERROR'))
        log(level, await state_message())
        level === 'ERROR' ? process.exit(1) : await sleep(config.timings.health_interval)
    }
}

export const server_status = async () => {
    const [pid, health] = (await inspect_state()) ?? []

    if (!pid) {
        status.alert('server is down')
        return set_pid(null)
    } else status.info(`server is running (pid: ${pid})`)

    if (health) status.success(`server is healthy and responding on port ${config.port}`)
    else status.alert('server is unresponsive to health checks')

    const { output, error, code } = run(
        (process.platform === 'win32'
            && pwsh_command(
                `ps -id ${pid} -erroraction silentlycontinue | `
                    + `select -p @{n='PID'; e={$_.id}}, @{n='PPID'; e={$_.parent.id}},`
                    + `@{n='%CPU'; e={$_.cpu}}, @{n='%MEM'; e={$_.workingset/1kb}},`
                    + `@{n='ELAPSED'; e={$_.starttime.tostring('hh:mm:ss')}},`
                    + `@{n='CMD';e={$_.path}}`,
            ))
            || `ps -p "${pid}" -o pid,ppid,pcpu,pmem,etime,cmd 2>/dev/null || true`,
    )

    if (!(error ?? code)) return status.info(`resource usage: ${output}`.trim())
    else return status.error(output, error ?? 'an unknown error occurred')
}

export const server_logs = (n = 50) => {
    /** @type string[] */
    const logs = readlines(file.log, n)
    /** @type string[] */
    const errors = readlines(file.err, n)

    if (logs.length) {
        status.info(`last ${n} lines from ${file.log}\n`)
        console.log(logs.join('\n'))
    }
    if (errors.length) {
        console.log()
        status.error(`last ${n} lines from ${file.err}\n`)
        console.log(errors.join('\n'))
    }
}

export default Object.freeze({
    start: start_server,
    stop: stop_server,
    restart: restart_server,
    monitor: monitor_server,
    status: server_status,
    logs: server_logs,
    help: show_help,
    clean: clean_logs,
})
