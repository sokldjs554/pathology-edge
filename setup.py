from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

setup(ext_modules=[Pybind11Extension('pathology_edge._patch_cpp', ['cpp/patches.cpp'],
                                     cxx_std=17, extra_compile_args=['-O3', '-pthread'],
                                     extra_link_args=['-pthread'])],
      cmdclass={'build_ext': build_ext})
