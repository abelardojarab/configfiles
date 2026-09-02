class jenkins_agent (
  String $jenkins_url = 'https://jaraberrocal.readmyblog.org/jenkins/',
) {
  # Each JNLP agent secret is tied to that host's node object in Jenkins
  # (Manage Jenkins > Nodes > <name> > connection command). A host only
  # gets set up here once it has a node registered on the controller.
  $agent_secrets = {
    'thunderx2' => '131b136ee7db1ae92b0fef10fbe69b80b740a78558f6f2feca45bcbd8ae5cb4c',
    'ubuntu06'  => 'dfa35149ff8277bab5843df9e0beee2ddbe6c4e2050fc554f524ba70f0be8caa',
    'ubuntu07'  => 'cb1cfb855b5b3718dff7d468533616bea21c000d645546ba148f42cd26e7455b',
    'ubuntu03'  => '24ab9a088e71271cb5cc0a2beac65478361e3933df0ab4361cd942451849e9c2',
    'ubuntu05'  => 'd0c59705bd4ba5d1e6e327ad662a7823a81b42cac85bf6991a9be343aeb3a83e',
  }

  $hostname = $facts['networking']['hostname']

  if $hostname in $agent_secrets {
    $secret = $agent_secrets[$hostname]

    file { '/opt/jenkins':
      ensure => directory,
      owner  => 'jenkins',
      group  => 'jenkins',
    }

    exec { 'download-jenkins-agent-jar':
      command => "curl -sL -o /opt/jenkins/agent.jar ${jenkins_url}jnlpJars/agent.jar",
      path    => ['/usr/bin', '/bin'],
      creates => '/opt/jenkins/agent.jar',
      require => File['/opt/jenkins'],
    }

    file { '/opt/jenkins/agent.jar':
      owner   => 'jenkins',
      group   => 'jenkins',
      require => Exec['download-jenkins-agent-jar'],
    }

    file { '/etc/systemd/system/jenkins-agent.service':
      ensure  => file,
      content => @("EOT"/L),
        [Unit]
        Description=Jenkins Slave
        Wants=network.target
        After=network.target

        [Service]
        User=jenkins
        ExecStart=java -jar /opt/jenkins/agent.jar -url ${jenkins_url} -secret ${secret} -name ${hostname} -webSocket -workDir "/home/jenkins"
        Restart=always
        RestartSec=10
        StartLimitInterval=0

        [Install]
        WantedBy=multi-user.target
        | EOT
      notify  => [Exec['jenkins-agent-daemon-reload'], Service['jenkins-agent']],
    }

    exec { 'jenkins-agent-daemon-reload':
      command     => 'systemctl daemon-reload',
      path        => ['/usr/bin', '/bin'],
      refreshonly => true,
    }

    service { 'jenkins-agent':
      ensure  => running,
      enable  => true,
      require => [File['/etc/systemd/system/jenkins-agent.service'], File['/opt/jenkins/agent.jar']],
    }
  }
}
