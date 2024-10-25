#general
alias als='cd ; nano .bash_aliases'
alias ..='cd ../'
alias dcupre='docker compose pull ; docker compose down ; docker compose up -d'
alias update='sudo apt-get update && sudo apt-get upgrade'
alias ctrs='docker ps -a'
alias ll='ls -a'
#directory speeddial
alias proj='cd ; cd project_crosbies/docker'
alias cdn8n='cd ; cd project_crosbies/docker/isolated_components/n8n'
alias cdbase='cd ; cd project_crosbies/docker/isolated_components/baserow'
alias cddoca='cd ; cd project_crosbies/docker/isolated_components/docassemble'
#n8n specific
alias updaten8n='cdn8n ; dcupre'
alias stopn8n='cdn8n ; docker compose down'
alias runn8n='cdn8n ; docker compose up -d'
#baserow specific
alias stopbr='cd ; cdbase ; docker compose down'
alias runbr='cd ; cdbase ; docker compose up -d'
alias restartbr='stopbr ; runbr'
alias updatebr='cdbase ; dcupre'
alias backupbr='stopbr ; docker run --rm -v baserow_data:baserow/data -v $PWD:/backup ubuntu tar cvf /backup/backup.tar /baserow/data ; stopbr ; runbr' 
alias restorebr='backupbr ; stopbr ; docker run --rm -v new_baserow_data_volume:/results -v $PWD:/backup ubuntu bash -c "mkdir -p /results/ && cd /results && tar xvf /backup/backup.tar --strip 2" ; rm_br ; run_br'
#docassemble specific
alias updatedoca='cddoca ; dcupre'
alias stopdoca='cddoca ; docker compose down'
alias rundoca='cddoca ; docker compose up -d'
#across multiple directories
alias daily='update ; proj ; dcupre ; cd'
alias pcycle='pstop ; pstart'
alias pstart='proj ; docker compose up -d ; docker compose logs -f'
alias pstop='proj ; docker compose down'
alias pupdate='proj ; dcupre'
