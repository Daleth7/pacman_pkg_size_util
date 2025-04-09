from typing import List, Mapping, Literal

type byte = float

class PkgInfo:
    def __init__(self, **kwargs) -> None:
        self.repository    : str              = kwargs['Repository']
        self.name          : str              = kwargs['Name']
        self.version       : str              = kwargs['Version']
        self.description   : str              = kwargs['Description']
        self.architecture  : str              = kwargs['Architecture']
        self.url           : str              = kwargs['URL']
        self.licenses      : str              = kwargs['Licenses']
        self.groups        : str              = kwargs['Groups']
        self.provides      : List[str]        = kwargs['Provides']
        self.dependencies  : List[str | Self] = kwargs['Depends On']
        self.optionals     : List[str | Self] = kwargs['Optional Deps']
        self.conflicts     : str              = kwargs['Conflicts With']
        self.replaces      : str              = kwargs['Replaces']
        self.download_size : byte             = kwargs['Download Size']
        self.install_size  : byte             = kwargs['Installed Size']
        self.packager      : str              = kwargs['Packager']
        self.build_date    : str              = kwargs['Build Date']
        self.validated_by  : str              = kwargs['Validated By']

        self.sizes : Mapping[str, byte] = {}

    def update_sizes(self) -> None:
        dep_download_total : byte = 0.0
        dep_install_total : byte = 0.0
        if self.dependencies is not None:
            for dep in self.dependencies:
                dep.update_sizes()
                dep_download_total += dep.total_size_raw('download')
                dep_install_total += dep.total_size_raw('install')
        opt_download_total : byte = 'N/A'
        opt_install_total : byte = 'N/A'

        self.sizes['download (self)'] = self.download_size
        self.sizes['install (self)'] = self.install_size
        self.sizes['download (dep)'] = dep_download_total
        self.sizes['install (dep)'] = dep_install_total
        self.sizes['download (opt)'] = opt_download_total
        self.sizes['install (opt)'] = opt_install_total

    def total_size_raw(self, which : Literal['install', 'download']) -> byte:
        return self.sizes[f'{which} (self)'] + self.sizes[f'{which} (dep)']

    @staticmethod
    def format_size(raw : float) -> str:
        if raw < 2**10:
            return f'{int(raw):,} bytes'
        elif raw < 2**20:
            return f'{raw/(2**10):,.1f} kiB'
        elif raw < 2**30:
            return f'{raw/(2**20):,.1f} MiB'
        else:
            return f'{raw/(2**30):,.1f} GiB'

    def total_size(self, which : Literal['install', 'download']) -> str:
        return PkgInfo.format_size( float(self.total_size_raw(which)) )