import { spawnSync } from 'node:child_process'
import { appendFileSync, existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { signal } from './constants.mjs'
/** @param commands {string[]} */
export const join_command = (...commands) => commands.join('; ')

/** @param commands {string[]} */
export const pwsh_command = (...commands) => `pwsh -noni -nop -c "${join_command(...commands)}"`

/** @param name {string} */
export const test_command = name =>
    !!run(
        (process.platform == 'win32' && pwsh_command(`(gcm ${name} -erroraction ignore).path`))
            || `which ${name}`,
    ).output

/** @param x {string} @returns {number | void} */
export const as_num = x => {
    try {
        return Number.parseInt(x)
    } catch {}
}

export const timestamp = () => `[${new Date().toLocaleTimeString()}]`

/** @type (pid: number, sig: keyof signal) => true */
export const send_signal = (pid, sig) => process.kill(pid, signal[sig])

/**
@type <C extends (() => any) = () => undefined>(
        delay: number,
        callback?: C,
        convert_to_ms?: boolean
    ) => Promise<C extends undefined ? undefined
            : C extends () => Promise ? Awaited<ReturnType<C>>
            : C extends () => any ? ReturnType<C>
            : never
    >
 */
export const sleep = async (delay, callback, convert_to_ms = true) => {
    if (convert_to_ms) delay = delay * 1000
    await new Promise(resolve => setTimeout(resolve, delay))

    /**
    @type typeof callback extends undefined ? undefined
        : typeof callback extends () => Promise ? Awaited<ReturnType<typeof callback>>
        : typeof callback extends () => any ? ReturnType<typeof callback>
        : never
     */
    return (
        callback ?
            callback.constructor.name === 'AsyncFunction' ?
                await callback()
            :   callback()
        :   undefined
    )
}

/** @param file {import('node:fs').PathOrFileDescriptor} @param text {string[]} */
export const write = (file, ...text) => {
    try {
        appendFileSync(file, text.join('\n'), { encoding: 'utf-8' })
    } catch {
        overwrite(file, ...text)
    }
}

/** @param file {import('node:fs').PathOrFileDescriptor} @param text {string[]} */
export const overwrite = (file, ...text) => writeFileSync(file, text.join('\n'), { encoding: 'utf-8' })

/** @param file {import('node:fs').PathLike} */
export const cat = file => {
    if (existsSync(file)) return readFileSync(file, { encoding: 'utf-8' }).trim()
    else return ''
}

/** @param file {string} */
export const safe_rm = file => existsSync(file) && rmSync(file)

/** @param file {import('node:fs').PathLike} @param n {number} */
export const readlines = (file, n = -1) => {
    const lines = cat(file).split('\n').filter(Boolean)
    if (n != -1 && lines.length > n + 1) return lines.slice(lines.length - n)
    else return lines
}

/** @param cmd {string} @param shell {boolean} */
export const run = cmd => {
    const { status, output, ...rest } = spawnSync(cmd, { shell: true })
    return { code: status, output: output?.map(x => x?.toString('utf-8').trim()).join('\n') ?? '', ...rest }
}
