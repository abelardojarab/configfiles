class my_zabbix {
  apt::source { 'zabbix':
    location => 'https://repo.zabbix.com/zabbix/6.0/ubuntu',
    release  => 'focal',   # zabbix has no resolute dist yet
    repos    => 'main',
    key      => {
      name   => 'zabbix.asc',
      source => 'https://repo.zabbix.com/zabbix-official-repo.key',
    },
  }
  ~> Class['apt::update']

  class { 'zabbix::agent':
    server      => '100.78.48.121',
    manage_repo => false,
    require     => Class['apt::update'],
  }

  # NVIDIA GPU monitoring (https://github.com/plambe/zabbix-nvidia-smi-multi-gpu).
  # Deployed on every node; harmless where nvidia-smi is absent. Actual
  # monitoring is enabled per-host by linking the template in the Zabbix UI.
  file { '/etc/zabbix/scripts':
    ensure  => directory,
    require => Class['zabbix::agent'],
  }

  file { '/etc/zabbix/scripts/get_gpus_info.sh':
    ensure  => file,
    mode    => '0755',
    content => @(EOT),
      #!/bin/bash

      result=$(/usr/bin/nvidia-smi -L)
      first=1

      echo "{"
      echo "\"data\":["

      while IFS= read -r line
      do
        if (( "$first" != "1" ))
        then
          echo ,
        fi
        index=$(echo -n $line | cut -d ":" -f 1 | cut -d " " -f 2)
        gpuuuid=$(echo -n $line | cut -d ":" -f 3 | tr -d ")" | tr -d " ")
        echo -n {"\"{#GPUINDEX}"\":\"$index"\", \"{#GPUUUID}"\":\"$gpuuuid\"}
        if (( "$first" == "1" ))
        then
          first=0
        fi
      done < <(printf '%s\n' "$result")

      echo
      echo "]"
      echo "}"
      | EOT
    require => File['/etc/zabbix/scripts'],
  }

  file { '/etc/zabbix/zabbix_agentd.d/nvidia-smi.conf':
    ensure  => file,
    mode    => '0644',
    content => @(EOT),
      UserParameter=gpu.number,/usr/bin/nvidia-smi -L | /usr/bin/wc -l
      UserParameter=gpu.discovery,/etc/zabbix/scripts/get_gpus_info.sh
      UserParameter=gpu.fanspeed[*],nvidia-smi --query-gpu=fan.speed --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.power[*],nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.temp[*],nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.utilization[*],nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.memutilization[*],nvidia-smi --query-gpu=utilization.memory --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.memfree[*],nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.memused[*],nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.memtotal[*],nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i $1 | tr -d "\n"
      UserParameter=gpu.utilization.dec.min[*],nvidia-smi -q -d UTILIZATION -i $1 | grep -A 5  DEC | grep Min | tr -s ' ' | cut -d ' ' -f 4
      UserParameter=gpu.utilization.dec.max[*],nvidia-smi -q -d UTILIZATION -i $1 | grep -A 5  DEC | grep Max | tr -s ' ' | cut -d ' ' -f 4
      UserParameter=gpu.utilization.enc.min[*],nvidia-smi -q -d UTILIZATION -i $1 | grep -A 5  ENC | grep Min | tr -s ' ' | cut -d ' ' -f 4
      UserParameter=gpu.utilization.enc.max[*],nvidia-smi -q -d UTILIZATION -i $1 | grep -A 5  ENC | grep Max | tr -s ' ' | cut -d ' ' -f 4
      | EOT
    require => Class['zabbix::agent'],
    notify  => Service['zabbix-agent'],
  }
}
