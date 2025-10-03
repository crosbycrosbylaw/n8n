import path from 'node:path'

const script_root = path.dirname(process.argv[1]).normalize()

/**
 * @param obj {Record<string, number | string | boolean>}
 * @returns {Readonly<Record<string, string>>}
 */
const environment = obj =>
    Object.freeze(
        Object.fromEntries(Object.entries({ ...obj, ...process.env }).map(([k, v]) => [k, String(v)])),
    )

const resolve_port = () => {
    if (!process.env.N8N_PORT) return 5678
    return Number.parseInt(process.env.N8N_PORT)
}

// --
export const logs_root = path.join(script_root, 'logs')

export const help_message = `
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

/** @type {unique symbol} */
const _unit = Symbol('unit')
/**
 * @type {Readonly<{
 *  [_unit]?: 'seconds'
 *  startup_timeout: number,
 *  restart_delay: number,
 *  health_interval: number
 * }>}
 */

const timings = Object.freeze({ startup_timeout: 60, restart_delay: 10, health_interval: 30 })

export const config = Object.freeze({ timings, port: resolve_port(), max_restarts: 5 })

export const signal = Object.freeze({ 0: 0, SIGTERM: 'SIGTERM', SIGKILL: 'SIGKILL', SIGINT: 'SIGINT' })

export const file = {
    pid: path.join(logs_root, 'n8n.pid'),
    log: path.join(logs_root, 'n8n-server.log'),
    err: path.join(logs_root, 'n8n-error.log'),
}

export const spawn_options = Object.freeze({
    stdio: 'inherit',
    shell: true,
    env: environment({
        N8N_RUNNERS_ENABLED: true,
        N8N_BLOCK_ENV_ACCESS_IN_NODE: false,
        N8N_GIT_NODE_DISABLE_BARE_REPOS: false,
        DB_SQLITE_POOL_SIZE: 1,
        GENERIC_TIMEZONE: 'America/Chicago',
        N8N_DIAGNOSTICS_ENABLED: false,
        N8N_EDITOR_BASE_URL: 'https://ccn8n.org',
        NODE_ENV: 'production',
        N8N_HOST: 'localhost',
        N8N_PORT: 5678,
        N8N_PROTOCOL: 'http',
        N8N_LOG_LEVEL: 'info',
        N8N_USER_FOLDER: script_root,
        N8N_TEMPLATES_ENABLED: false,
        N8N_PREVIEW_MODE: true,
    }),
})

export default { config, file, signal, spawn_options }


