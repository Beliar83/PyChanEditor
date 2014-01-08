'''
Created on 17.12.2013

@author: Karsten
'''

import os

from fife import fife
from fife.extensions.fife_settings import Setting


from application import EditorApplication

print ("Using the FIFE python module found here: ",
        os.path.dirname(fife.__file__))

TDS = Setting(app_name="PyChanEditor", settings_file="./settings.xml")

def main():
    app = EditorApplication(TDS)
    app.run()
    
if __name__ == '__main__':
    main()