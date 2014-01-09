"""
PyChanEditor Copyright (C) 2014 Karsten Bock

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import os

from fife import fife
from fife.extensions.fife_settings import Setting


from editor.application import EditorApplication

print ("Using the FIFE python module found here: ",
        os.path.dirname(fife.__file__))

TDS = Setting(app_name="PyChanEditor", settings_file="./settings.xml")

def main():
    app = EditorApplication(TDS)
    app.run()
    
if __name__ == '__main__':
    main()