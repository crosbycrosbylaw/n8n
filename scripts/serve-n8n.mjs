import chalk from "chalk"
import subprocess from "node:child_process"
import fs from "node:fs"
import path from "node:path"

// -- CONSTANTS -- //

const signal = Object.freeze({
    0: 0,
    SIGTERM: "SIGTERM",
    SIGKILL: "SIGKILL",
    SIGINT: "SIGINT",
})

const help_message = `
usage: ${path.parse(process.argv[1]).base} COMMAND [ ...options ]

commands:
  start         - Start n8n server
  stop          - Stop n8n server
  restart       - Restart n8n server
  status        - Show server status
  monitor       - Start server with auto-restart monitoring
  logs [lines]  - Show server logs (default: 50 lines)
  help          - Show this help message

environment variables:
  N8N_PORT - Port for n8n server (default: 5678)
`

// -- CONFIGURATION -- //

const script_root = path.dirname(process.argv[1]).normalize()
const project_root = path.join(script_root, "..")
const logs_root = path.join(project_root, "logs")
const paths = {
    pid: path.join(logs_root, "n8n.pid"),
    log: path.join(logs_root, "n8n-server.log"),
    err: path.join(logs_root, "n8n-error.log"),
}

const resolve_port = () => {
    if (!process.env.N8N_PORT) return 5678
    return Number.parseInt(process.env.N8N_PORT)
}

const config = Object.freeze({
    max_restarts: 5,
    restart_delay: 10,
    health_interval: 30,
    port: resolve_port(),
})

// -- UTILITY METHODS -- //

const timestamp = () => `[${new Date().toLocaleTimeString()}]`
/** @type (pid: number, sig: keyof signal) => true */
const send_signal = (pid, sig) => process.kill(pid, signal[sig])
/**
 * @param delay {number}
 * @param callback {() => void | undefined}
 * @param convert_to_ms {boolean}
 */
const sleep = (delay, callback = undefined, convert_to_ms = true) => {
    if (convert_to_ms) delay = delay * 1000
    return new Promise((resolve) => setTimeout(() => resolve(callback && callback()), delay))
}
/** @param err {unknown} */
const raise = (err) => {
    if (err) throw err
}

/** @param file {fs.PathOrFileDescriptor} @param text {string[]} */
const write = (file, ...text) => {
    try {
        fs.appendFileSync(file, text.join("\n"), { encoding: "utf-8" })
    } catch {
        overwrite(file, ...text)
    }
}
/** @param file {fs.PathOrFileDescriptor} @param text {string[]} */
const overwrite = (file, ...text) => fs.writeFileSync(file, text.join("\n"), { encoding: "utf-8" })
/** @param file {fs.PathLike} */
const cat = (file) => {
    if (fs.existsSync(file)) return fs.readFileSync(file, { encoding: "utf-8" })
    else return ""
}
/** @param file {fs.PathLike} @param n {number} */
const readlines = (file, n = -1) => {
    const lines = cat(file).split("\n").filter(Boolean)
    if (lines.length > n + 1) return lines.slice(lines.length - n)
    else return lines
}
// -- LOGGING METHODS -- //

const setup_logging = () => {
    if (!fs.existsSync(logs_root)) fs.mkdirSync(logs_root)
    const now = new Date(),
        text = `\n[${now.toLocaleTimeString()}] ${now.toLocaleDateString()} - '${path.parse(process.argv[1]).name}.mjs'\n`
    ;[paths.log, paths.err].forEach((f) => write(f, text))
}

const status = {
    /**@type  (...msg: (string | Error)[]) => void */
    error: (...msg) => console.error(chalk.red("ERROR ") + msg.join("\n")),
    /**@type  (...msg: string[]) => void */
    alert: (...msg) => console.log(chalk.yellow(msg.join("\n"))),
    /**@type  (...msg: string[]) => void */
    info: (...msg) => console.log(chalk.blue("INFO ") + msg.join("\n")),
    /**@type  (...msg: string[]) => void */
    success: (...msg) => console.log(chalk.green(msg.join("\n"))),
}

/**@type  (lvl: string | null, ...msg: string[]) => void */
const log = (lvl, ...msg) => {
    const key = lvl?.toLowerCase() ?? ""
    if (key in status) status[key](...msg)

    let level = key,
        file = paths.log

    switch (level) {
        case "alert":
            level = "warn"
            break
        case "error":
            file = paths.err
            break
        default:
            level = "info"
    }

    write(file, `${timestamp()} ${level.toUpperCase()} ${msg.join("\n")}\n`)
}

// -- PROCESS METHODS -- //

/** @param pid {string | number | null} */
const set_pid = (pid) => {
    if (pid == null && fs.existsSync(paths.pid)) return fs.rmSync(path.normalize(paths.pid))
    return overwrite(paths.pid, pid?.toString())
}

/** @returns {number | void} */
const get_pid = () => {
    const pid_str = cat(paths.pid).trim()
    return (pid_str && Number.parseInt(pid_str)) ?? void pid_str
}

/** @param cmd {string} @param shell {boolean} */
const run = (cmd, shell = false) => {
    const { status, ...rest } = subprocess.spawnSync(cmd, { shell })
    return { code: status, ...rest }
}

const serve = () => {
    return subprocess.spawn("npx", ["n8n"], {
        stdio: "inherit",
        shell: true,
    })
}

// -- CONDITIONALS -- //

/** @returns {number | void} */
const is_running = () => {
    try {
        const pid = get_pid()
        if (!pid) throw null
        send_signal(pid, 0)
        return pid
    } catch {
        return undefined
    }
}

const is_healthy = () => !run(`curl -f -s "http://localhost:${config.port}/"`).code

// -- COMMAND FUNCTIONS -- //

const start_server = async () => {
    const existing_pid = is_running()
    if (existing_pid) return log("INFO", `server is already running (pid: ${existing_pid})`)

    log("INFO", "starting n8n server")
    const proc = serve()

    set_pid(proc.pid)

    await sleep(5, async () => {
        if (!is_running()) {
            log("ERROR", "n8n server failed to start")
            set_pid(null)
        } else {
            log("SUCCESS", "n8n server started successfully")

            let attempts = 0
            const max_attempts = 10

            status.alert("waiting for server to be ready...")

            while (attempts < max_attempts) {
                if (is_healthy())
                    return log("SUCCESS", `server is ready and responding on port ${config.port}`)
                else await sleep(3, () => attempts++)

                if (!is_running()) {
                    log("ERROR", "server process died during startup")
                    return set_pid(null)
                } else status.alert(`not ready yet (${attempts}/${max_attempts})`)
            }

            return log("ALERT", "health check failed, but the process is running")
        }
    })
}

const stop_server = async () => {
    const pid = is_running()

    if (!pid) return status.alert("server is not running")

    log("INFO", `stopping n8n server (pid: ${pid})...`)

    /** @param id {number} */
    const try_kill = (id = pid) => {
        try {
            return send_signal(id, signal.SIGTERM)
        } catch {
            return false
        }
    }

    if (!try_kill()) {
        let ct = 0
        while (ct < 10 && !try_kill()) await sleep(1, () => ct++)
        const pid = is_running()
        if (pid) {
            status.alert("graceful shutdown failed; force killing...")
            send_signal(pid, signal.SIGKILL)
        }
    }

    set_pid(null)
    log("SUCCESS", "server stopped successfully")
}

const monitor_server = async () => {
    let ct = 0

    log("INFO", "starting server monitor with auto-restart enabled")

    while (true) {
        if (!is_running()) {
            if (ct >= config.max_restarts)
                return log("ERROR", "maximum restart attempts exceeded. exiting.")

            log("ALERT", `server is not running. restarting (${ct}/${config.max_restarts})...`)

            await start_server().then(async () => {
                if (is_running()) return log("SUCCESS", "server restarted successfully")
                log("ERROR", `restart attempt failed. waiting ${config.restart_delay} seconds...`)
                await sleep(config.restart_delay, () => ct++)
            })
        } else if (!is_healthy()) {
            log("ALERT", "health check failed, but server is running")
        }

        await sleep(config.health_interval)
    }
}

const server_status = async () => {
    const pid = is_running()
    if (pid) {
        status.info(`n8n server is running (pid: ${pid})`)
        if (is_healthy()) {
            status.success(`server is ready and responding on port ${config.port}`)
        } else {
            status.alert("server is unresponsive to health checks")
        }
        const status_command = () => {
            switch (process.platform) {
                case "win32":
                    /** @param text {readonly string[]} */
                    return (
                        'pwsh -noni -nop -c "' +
                        `get-process -id ${pid} -erroraction silentlycontinue | ` +
                        "select-object -property " +
                        "@{n='PID';e={$_.id}}," +
                        "@{n='PPID';e={$_.parent.id}}," +
                        "@{n='%CPU';e={$_.cpu}}," +
                        "@{n='%MEM';e={$_.workingset/1kb}}," +
                        "@{n='ELAPSED';" +
                        "e={$_.starttime.tostring('hh:mm:ss')}}," +
                        "@{n='CMD';e={$_.path}}" +
                        '"'
                    )
                default:
                    return `ps -p "${pid}" -o pid,ppid,pcpu,pmem,etime,cmd 2>/dev/null || true`
            }
        }

        const { output, error, code } = run(status_command(), true)
        const output_text = output?.map((x) => x?.toString("utf-8")).join("\n")
        if (code == 0 && !error) {
            status.info(`resource usage: ${output_text}`.trim())
        } else {
            status.error(output_text, error)
        }
    } else {
        status.error("n8n server is not running")
    }
}

const server_logs = (n = 50) => {
    /** @type string[] */
    const logs = readlines(paths.log, n)
    /** @type string[] */
    const errors = readlines(paths.err, n)

    if (logs.length) {
        status.info(`last ${n} lines from ${paths.log}\n`)
        console.log(logs.join("\n"))
    }
    if (errors.length) {
        console.log()
        status.error(`last ${n} lines from ${paths.err}\n`)
        console.log(errors.join("\n"))
    }
}

// -- MAIN -- //

const server = Object.freeze({
    start: start_server,
    stop: stop_server,
    restart: async () => {
        status.info("restarting n8n server...")
        stop_server()
            .then(async () => await sleep(2, start_server))
            .catch(raise)
    },
    monitor: monitor_server,
    status: server_status,
    logs: server_logs,
    help: () => console.log(help_message),
})

if (import.meta.main) {
    setup_logging()

    const [_executable, _script, command = "start", ...args] = process.argv

    if (command in server) {
        switch (command) {
            case "logs":
                server.logs(Number.parseInt(args.at(0) || "50"))
                break
            default:
                server[command]()
        }
    } else {
        status.error("unknown command")
        process.exit(1)
    }
}
