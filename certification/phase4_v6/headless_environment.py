"""Prospective child-environment repair; consumed notebook sources stay frozen."""
from certification.phase4_v6.clean_environment import CleanEnvironment


class HeadlessEnvironment(CleanEnvironment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env['MPLBACKEND'] = 'Agg'
        self.env['MPLCONFIGDIR'] = str(self.scratch/'matplotlib')
