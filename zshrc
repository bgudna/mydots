# Add deno completions to search path
if [[ ":$FPATH:" != *":/Users/dns/.zsh/completions:"* ]]; then export FPATH="/Users/dns/.zsh/completions:$FPATH"; fi
PROMPT="%{$fg_bold[white]%}%n"
PROMPT+=" %(?:%{$fg_bold[green]%}@ :%{$fg_bold[red]%}➜ )"
PROMPT+="%{$fg[cyan]%}%~%{$reset_color%} %(?:%{$fg_bold[green]%}➜ "
export RACK_DIR=/Users/bgudna/code/other/Rack-SDK/
export PATH=$PATH:/Users/bgudna/.local/bin/

alias tube='python3 ~/code/mydots/scripts/ytwrap.py'

# Autoload zsh add-zsh-hook and vcs_info functions (-U autoload w/o substition,
autoload -Uz add-zsh-hook vcs_info
# Enable substitution in the prompt.
setopt prompt_subst
# Run vcs_info just before a prompt is displayed (precmd)
add-zsh-hook precmd vcs_info
# add ${vcs_info_msg_0} to the prompt
# e.g. here we add the Git information in red  
PROMPT+='%F{cyan}${vcs_info_msg_0_}%f '
#
# Enable checking for (un)staged changes, enabling use of %u and %c
zstyle ':vcs_info:*' check-for-changes true
# Set custom strings for an unstaged vcs repo changes (*) and staged changes
zstyle ':vcs_info:*' unstagedstr ' *'
zstyle ':vcs_info:*' stagedstr ' +'
# Set the format of the Git information for vcs_info
zstyle ':vcs_info:git:*' formats       '(%b%u%c)'
zstyle ':vcs_info:git:*' actionformats '(%b|%a%u%c)'

export GPG_TTY=$(tty)

# Added by LM Studio CLI (lms)
export PATH="$PATH:/Users/dns/.lmstudio/bin"
# End of LM Studio CLI section

export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
. "/Users/dns/.deno/env"
# Initialize zsh completions (added by deno install script)
autoload -Uz compinit
compinit
