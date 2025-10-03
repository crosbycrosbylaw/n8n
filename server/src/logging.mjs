import chalk from "chalk"
import { existsSync, mkdirSync } from "node:fs"
import { file, logs_root } from "./constants.mjs"
import { cat, timestamp, write } from "./utils.mjs"

export const setup_logging = () => {
    if (!existsSync(logs_root)) mkdirSync(logs_root)
    ;[file.log, file.err].forEach((f) => cat(f) && write(f, "\n"))
}

export const status = {
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
export const log = (lvl, ...msg) => {
    const key = lvl?.toLowerCase() ?? ""
    if (key in status) status[key](...msg)

    let level = key,
        path = file.log

    switch (level) {
        case "alert":
            level = "warn"
            break
        case "error":
            path = file.err
            break
        default:
            level = "info"
    }

    write(path, `${timestamp()} ${level.toUpperCase()} ${msg.join("\n")}\n`)
}
