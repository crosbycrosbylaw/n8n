#!/usr/bin/env node
import server from '../src/index.mjs'

async function main() {
    const [_executable, _script, command = 'start', ...args] = process.argv

    if (command in server) {
        switch (command) {
            case 'clean':
            case 'help':
                server[command]()
                break
            case 'logs':
                server.logs(Number.parseInt(args?.at(0) ?? '50'))
                break
            default:
                await server[command]()
        }
    } else {
        server.help()
        process.exit(1)
    }
}

if (import.meta.main) await main()
