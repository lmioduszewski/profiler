from .xsection_plugin_main import XSectionPlugin
import sys
from pathlib import Path

# Add path
custom_package_dir = Path(r'C:\Users\lukem\Python\Projects')

# Convert the Path object to a string (if not already a string in Python 3.8 and later) and append it to sys.path
if str(custom_package_dir) not in sys.path:
    sys.path.append(str(custom_package_dir))


def classFactory(iface):
    print('initializing profile plugin')
    return XSectionPlugin(iface)
