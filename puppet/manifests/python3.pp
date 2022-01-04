include apt

class python3 {
    apt::ppa { 'ppa:deadsnakes/ppa':
    } ->

    package { ["python3-sqlalchemy", "python3-pandas", "python3-numpy", "python3-scipy", "python3-matplotlib", "python3-jsonschema",
               "python3-jedi", "python3-xlrd", "python3-pytest", "python3-nose2", "python3-setuptools", "python3-wheel", "python3-pip",
               "python3-venv", "python3-prettytable", "python3-pygments"]:
        ensure => installed,
    }
}
