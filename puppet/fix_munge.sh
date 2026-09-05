#!/bin/bash
sudo systemctl stop munge

export MUNGEUSER=3456
usermod -u $MUNGEUSER munge
groupmod -g $MUNGEUSER munge

mkdir -p /etc/munge /var/log/munge /var/lib/munge /run/munge
echo "mungemungemungemungemungemungemunge" > /etc/munge/munge.key
chown -R munge:munge /etc/munge/ /var/log/munge/ /var/lib/munge/ /run/munge/
chmod 0700 /etc/munge/ /var/log/munge/ /var/lib/munge/
chmod 0755 /run/munge/

sudo systemctl enable munge
sudo systemctl start munge

export SLURMUSER=3457
usermod -u $SLURMUSER slurm
groupmod -g $SLURMUSER slurm

if [ -d /etc/slurm ] && [ ! -d /etc/slurm-llnl ] && [ ! -L /etc/slurm-llnl ]; then
  ln -s /etc/slurm /etc/slurm-llnl
fi
if [ ! -d /etc/slurm-llnl ]; then
  mkdir -p /etc/slurm-llnl
fi

mkdir -p /var/lib/slurm-llnl/slurmd
mkdir -p /var/lib/slurm-llnl/slurmctld
mkdir -p /var/log/slurm-llnl
mkdir -p /var/run/slurm-llnl

chown -R slurm:slurm /var/lib/slurm* /var/log/slurm* /var/run/slurm*

echo CgroupMountpoint=/sys/fs/cgroup | sudo tee /etc/slurm-llnl/cgroup.conf
