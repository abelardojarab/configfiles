include apt

class python3 {
  apt::ppa { 'ppa:deadsnakes/ppa': } ~> Class['apt::update']
  apt::ppa { 'ppa:ubuntuhandbook1/octave': } ~> Class['apt::update']

  package { [
    'pylint','flake8','python3-yapf','python3-sqlalchemy',
    'python3-pandas','python3-numpy','python3-scipy',
    'python3-matplotlib','python3-boto3','python3-jsonschema',
    'black','python3-autopep8','python3-pycodestyle','python3-jedi',
    'python3-xlrd','python3-gridfs','python3-pytest','python3-nose2',
    'python3-setuptools','python3-wheel','python3-pip','python3-venv',
    'python3-plotly','python3-colorlog','python3-selenium',
    'python3-prettytable','python3-tables','python3-seaborn',
    'python3-yaml','python3-pygments','python3-flask','python3-paramiko',
    'python3-opencv','python3-tqdm','python3-pygal','python3-openpyxl',
    'python3-xlsxwriter','python3-influxdb','python3-sklearn',
    'cython3','pybind11-dev','python3-dev','python3-pycparser',
    'python3-cffi','python3-jupyter-core','python3-jupyter-client',
    'python3-zeroconf','python3-regex','python3-serial',
    'python3-pomegranate','python3-networkx','python3-testresources',
    # pick the notebook package that exists on your Ubuntu:
    'python3-notebook',
    # if we want multiple interpreters from deadsnakes:
    # 'python3.9','python3.9-venv','python3.9-full',
    # 'python3.10','python3.10-venv',
  ]:
    ensure => installed,
    require => [ Class['apt::update'] ],
  }

  # exec { 'update-alternatives-python3':
  #   command => 'update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && update-alternatives --set python3 /usr/bin/python3.9',
  #   unless  => 'update-alternatives --query python3 | grep -q "/usr/bin/python3.9"',
  #   path    => ['/bin', '/usr/bin', '/sbin', '/usr/sbin'],
  #   require => Package['python3.9-full'],
  # }

  # Ensure pip is upgraded before installing anything
  # exec { 'upgrade-pip':
  #   command => '/usr/bin/python3.9 -m pip install --upgrade pip',
  #   unless  => '/usr/bin/python3.9 -c "import pip; assert tuple(map(int, pip.__version__.split(\'.\'))) >= (23, 0, 0)"',
  #   path    => ['/bin', '/usr/bin', '/sbin', '/usr/sbin'],
  #   require => Package['python3.9-full'],
  # }

  # Force reinstall numpy, sympy, pandas, and pillow even if they are apt-installed
  # exec { 'fix-base-python-packages':
  #   command => '/usr/bin/python3.9 -m pip install --force-reinstall --no-cache-dir --ignore-installed --break-system-packages terminado mpmath numpy sympy pandas pillow matplotlib',
  #   unless  => '/usr/bin/python3.9 -c "import numpy, pandas, PIL, matplotlib; print(numpy.__version__)"',
  #   path    => ['/bin', '/usr/bin', '/sbin', '/usr/sbin'],
  #   require => Exec['upgrade-pip'],
  # }

  # Install required Python packages (ray, torch, torchvision, torchaudio, livelossplot), but skip if already installed via pip
  # exec { 'install-python-packages':
  #   command => '/usr/bin/python3.9 -m pip install ray[client] torch torchvision torchaudio livelossplot',
  #   unless  => '/usr/bin/python3.9 -c "import ray, torch, torchvision, torchaudio, livelossplot"',
  #   path    => ['/bin', '/usr/bin', '/sbin', '/usr/sbin'],
  #   require => Exec['fix-base-python-packages'],
  # }

  # Ensure Jupyter is installed via pip
  # exec { 'install-jupyter':
  #   command => '/usr/bin/python3.9 -m pip install --upgrade --ignore-installed pip jupyter jupyterlab',
  #   unless  => '/usr/bin/python3.9 -m pip show jupyter',
  #   path    => ['/bin', '/usr/bin', '/sbin', '/usr/sbin'],
  #   require => Package['python3.9-full'],
  # }

  # Define shared Python dist-packages directory
  $python_dist_packages = "/usr/lib/python3/dist-packages"

  # Ensure symlinks for Python 3.8 `.so` files exist for Python 3.9
  # exec { 'symlink-python38-so-files-to-39':
  #   command => "find ${python_dist_packages} -name '*.cpython-38-*.so' -exec sh -c 'ln -sf {} ${python_dist_packages}/$(basename {} | sed s/cpython-38/cpython-39/)' \\;",
  #   unless  => "find ${python_dist_packages} -name '*.cpython-39-*.so' | grep -q .",
  #   path    => ['/bin', '/usr/bin'],
  # }

}
