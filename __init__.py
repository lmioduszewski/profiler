from .xsection_plugin_main import XSectionPlugin


def classFactory(iface):
    print('initializing profile plugin')
    return XSectionPlugin(iface)
