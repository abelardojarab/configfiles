class nodes {
  package { 'tree-sitter-cli':
    ensure   => latest,
    provider => 'npm',
  }

  package { ['javascript-typescript-langserver', "bash-language-server", "yaml-language-server",
             'dockerfile-language-server-nodejs', 'pyright']:
               ensure   => latest,
               provider => 'npm',
  }
}
