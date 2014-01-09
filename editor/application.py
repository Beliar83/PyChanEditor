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

import gettext
import yaml
import os

from fife import fife

from fife.extensions import pychan
from fife.extensions.pychan import GuiXMLError
from fife.extensions.pychan.pychanbasicapplication import PychanApplicationBase
from fife.extensions.pychan.widgets import Container, VBox, HBox, ScrollArea
from fife.extensions.pychan.dialog.filebrowser import FileBrowser

from editor.gui.menubar import MenuBar, Menu
from editor.gui.action import Action
from editor.gui import action
from editor.gui.error import ErrorDialog
from xml.sax._exceptions import SAXParseException

class EditorEventListener(fife.IKeyListener, fife.ICommandListener):
    
    """Listener for the PyChanEditor"""
    def __init__(self, app):
        self.app = app
        self.engine = app.engine
        eventmanager = self.engine.getEventManager()
        fife.IKeyListener.__init__(self)
        eventmanager.addKeyListener(self)
        fife.ICommandListener.__init__(self)
        eventmanager.addCommandListener(self)

    def keyPressed(self, evt):  # pylint: disable-msg=W0221, C0103
        keyval = evt.getKey().getValue()
        if keyval == fife.Key.ESCAPE:
            self.app.quit()

    def keyReleased(self, evt):  # pylint: disable-msg=W0221, C0103
        pass

    def onCommand(self, command):  # pylint: disable-msg=W0221, C0103
        if command.getCommandType() == fife.CMD_QUIT_GAME:
            self.app.quit()
            command.consume()

class EditorApplication(PychanApplicationBase):
   
    DATA_PATH = "data/"
    FILEBROWSER_XML = DATA_PATH + "gui/filebrowser.xml"    
    MENU_HEIGHT = 30
    TOOLBAR_HEIGHT = 60
   
    def __init__(self, setting=None):
        PychanApplicationBase.__init__(self, setting)
        
        self.error_dialog = lambda msg: ErrorDialog(msg, self.DATA_PATH)
        
        vfs = self.engine.getVFS()
        vfs.addNewSource(self.DATA_PATH)
                    
        self.__languages = {}
        self.__current_language = ""
        default_language = setting.get("i18n", "DefaultLanguage", "en")
        languages_dir = setting.get("i18n", "Directory", "__languages")
        for language in setting.get("i18n", "Languages", ("en",)):
            fallback = (language == default_language)
            self.__languages[language] = gettext.translation("PyChanEditor",
                                                            languages_dir,
                                                            [language],
                                                            fallback=fallback)
        language = setting.get("i18n", "Language", default_language)
        self.switch_language(language)
        
        self._engine_settings = self.engine.getSettings()
        self._filename = None
        self._markers = {}
        self._main_window = None
        self._toolbar = None
        self._menubar = None
        self._bottom_window = None
        self._edit_window = None
        self._edit_wrapper = None
        self._property_window = None
        self._selected_widget = None
        self._project_data_path = None
        self._marker_dragged = False
        self._widget_dragged = False
        self._old_x = 0
        self._old_y = 0
        self.init_gui(self._engine_settings.getScreenWidth(),
                      self._engine_settings.getScreenHeight());

    def init_gui(self, screen_width, screen_height):
        """Initialize the gui
        
        Args:
        
            screen_width: The width the elements are sized to
            
            screen_height: The height the elements are sized to
        """
        self._main_window = VBox(min_size=(screen_width, screen_height),
                                 position=(0, 0), hexpand=1, vexpand=1)
        self._menubar = MenuBar(min_size=(screen_width, self.MENU_HEIGHT))
        self.init_menu_actions()
        self._main_window.addChild(self._menubar)
        self._toolbar = HBox(min_size=(screen_width, self.TOOLBAR_HEIGHT),
                             vexpand=0, hexpand=1)
        self._main_window.addChild(self._toolbar)
        self._bottom_window = HBox(border_size=1, vexpand=1, hexpand=1)
        self._edit_wrapper = ScrollArea(border_size=1, vexpand=1, hexpand=3)        
        self._edit_window = Container(parent=self._edit_wrapper)
        self._edit_window.capture(self.on_widget_selected, "mousePressed")
        self._edit_window.capture(self.on_widget_dragged, "mouseDragged")

        self._edit_wrapper.addChild(self._edit_window)
        self._bottom_window.addChild(self._edit_wrapper)
        self._property_window = Container(border_size=1, vexpand=1, hexpand=1)
        self._bottom_window.addChild(self._property_window)
        self._main_window.addChild(self._bottom_window)
        self._main_window.show()
        self.clear_gui()
        
    def init_menu_actions(self):
        """Initialize actions for the menu"""
        open_project_action = Action(_(u"Open"), "gui/icons/open_file.png")
        open_project_action.helptext = _(u"Open GUI file")
        action.activated.connect(self.on_open_project_action, sender=open_project_action)
        exit_action = Action(_(u"Exit"), "gui/icons/quit.png")
        exit_action.helptext = _(u"Exit program")
        action.activated.connect(self.quit, sender=exit_action)
        self._file_menu = Menu(name=_(u"File"))
        self._file_menu.addAction(open_project_action)
        self._file_menu.addSeparator()
        self._file_menu.addAction(exit_action)
        self._menubar.addMenu(self._file_menu)

    def get_widget_in(self, widget, x, y):
        point = fife.Point(x, y + self.MENU_HEIGHT + self.TOOLBAR_HEIGHT)
        abs_x, abs_y = widget.getAbsolutePos()
        rect = fife.Rect(abs_x, abs_y, 
                         widget.width, widget.height)
        if rect.contains(point):
            if hasattr(widget, "children"):
                for child in widget.children:
                    found = self.get_widget_in(child, x, y)
                    if found:
                        return found
                return widget
            else:
                return widget
                
        return None
    
    def on_widget_selected(self, event, widget):
        self._widget_dragged = False
        self._old_x = event.getX()
        self._old_y = event.getY()
        if self._marker_dragged:
            #Stops the editor from selecting another widget after a widget has
            #been resized by a marker
            self._marker_dragged = False
            return
        assert isinstance(event, fife.MouseEvent)
        assert isinstance(widget, pychan.Widget)
        real_widget = widget.real_widget
        assert isinstance(real_widget, fife.fifechan.Widget)
        clicked = self.get_widget_in(widget, event.getX(), event.getY())
        if clicked == widget:
            clicked = None
        #while(clicked):
        #    selected = clicked
        self.select_widget(clicked)
        #event.consume()

    def get_pos_in_scrollarea(self, widget):
        assert isinstance(widget, pychan.Widget)
        x = widget.x
        y = widget.y
        #fife.Rect.
        parent = widget.parent
        while parent is not self._edit_window:
            x += parent.x
            y += parent.y
            parent = parent.parent
        
        return x, y
    
    def on_marker_dragged(self, event, widget):
        assert isinstance(widget, pychan.Widget)
        old_x, old_y = self.get_pos_in_scrollarea(widget)
        rel_x = event.getX()
        rel_y = event.getY()
        new_x = old_x + rel_x
        new_y = old_y + rel_y
        marker = widget.name[-2:]
        if marker == "TL":
            if new_x >= self._markers["BR"].x:
                return
            if new_y >= self._markers["BR"].y:
                return
            self._selected_widget.x += rel_x
            self._selected_widget.y += rel_y
            self._selected_widget.width += rel_x * -1
            self._selected_widget.height += rel_y * -1
            widget.x += rel_x
            widget.y += rel_y
        if marker == "TR":
            if new_x <= self._markers["BL"].x:
                return
            if new_y >= self._markers["BL"].y:
                return
            self._selected_widget.y += rel_y
            self._selected_widget.width += rel_x
            self._selected_widget.height += rel_y * -1
            widget.x += rel_x
            widget.y += rel_y
        if marker == "BR":
            if new_x <= self._markers["TL"].x:
                return
            if new_y <= self._markers["TL"].y:
                return
            self._selected_widget.width += rel_x
            self._selected_widget.height += rel_y
            widget.x += rel_x
            widget.y += rel_y
        if marker == "BL":
            if new_x >= self._markers["TR"].x:
                return
            if new_y <= self._markers["TR"].y:
                return
            self._selected_widget.x += rel_x
            self._selected_widget.width += rel_x * -1
            self._selected_widget.height += rel_y
            widget.x += rel_x
            widget.y += rel_y
        self.position_markers()
    
    def on_marker_pressed(self, event, widget):
        self._marker_dragged = True

    def position_markers(self):
        """RePositions the markers on the selected wiget"""
        x, y = self.get_pos_in_scrollarea(self._selected_widget)
        x -= 5
        y -= 5
        self._markers["TL"].position = x, y
        x += self._selected_widget.width
        self._markers["TR"].position = x, y
        y += self._selected_widget.height
        self._markers["BR"].position = x, y
        x -= self._selected_widget.width
        self._markers["BL"].position = x, y

    def recreate_markers(self):
        """ReCreates the markers for the currently selected widget"""
        self.clear_markers()
        if self._selected_widget is None:
            return
        marker_tl = pychan.Icon(parent=self._edit_window,
            name="MarkerTL",
            size=(10, 10),
            image="gui\icons\marker.png")
        marker_tl.capture(self.on_marker_dragged, "mouseDragged")
        marker_tl.capture(self.on_marker_pressed, "mousePressed")
        self._edit_window.addChild(marker_tl)
        self._markers["TL"] = marker_tl
        marker_tr = pychan.Icon(parent=self._edit_window,
            name="MarkerTR",
            size=(10, 10),
            image="gui\icons\marker.png")
        marker_tr.capture(self.on_marker_dragged, "mouseDragged")
        marker_tr.capture(self.on_marker_pressed, "mousePressed")
        self._edit_window.addChild(marker_tr)
        self._markers["TR"] = marker_tr
        marker_br = pychan.Icon(parent=self._edit_window,
            name="MarkerBR",
            size=(10, 10),
            image="gui\icons\marker.png")
        marker_br.capture(self.on_marker_dragged, "mouseDragged")
        marker_br.capture(self.on_marker_pressed, "mousePressed")
        self._edit_window.addChild(marker_br)
        self._markers["BR"] = marker_br
        marker_bl = pychan.Icon(parent=self._edit_window,
            name="MarkerBL",
            size=(10, 10),
            image="gui\icons\marker.png")
        marker_bl.capture(self.on_marker_dragged, "mouseDragged")
        marker_bl.capture(self.on_marker_pressed, "mousePressed")
        self._edit_window.addChild(marker_bl)
        self._markers["BL"] = marker_bl
        self.position_markers()

    def select_widget(self, widget):
        """Sets a widget to be the currently selected one
        
        Args:
        
            widget: The widget
        """
        if widget is None:
            self._selected_widget = None
        else:
            assert isinstance(widget, pychan.Widget)
            self._selected_widget = widget
        self.recreate_markers()        

    def switch_language(self, language):
        """Switch to the given language
        
        Args:
        
            language: The name of the language to switch to
        """
        if not language in self.__languages:
            raise KeyError("The language '%s' is not available" % language)
        if not language == self.__current_language:
            self.__languages[language].install()
            self.__current_language = language    

    def clear_markers(self):
        """Removes the markers"""
        for marker in self._markers.itervalues():
            self._edit_window.removeChild(marker)
        self._markers = {}

    def clear_gui(self):
        """Clears the current gui file and markers"""
        self._edit_window.removeAllChildren()

    def on_open_project_action(self):
        """Display the filebrowser to selct a gui file to open"""
        browser = FileBrowser(self.engine, self.on_project_file_selected,
                              extensions=["pychan"],
                              guixmlpath=self.FILEBROWSER_XML)
        browser.setDirectory(".")
        browser.showBrowser()

    def on_project_file_selected(self, path, filename):
        """Called when a gui file was selected
        
        Args:

            path: Path to the selected file
            
            filename: The selected file
        """
        filepath = os.path.join(path, filename)
        project_file = file(filepath, "r")
        project = yaml.load(project_file)
        gui_path = os.path.join(path, project["settings"]["gui_path"])
        vfs = self.engine.getVFS()        
        assert isinstance(vfs, fife.VFS)
        vfs.addNewSource(gui_path)
        gui_filepath = os.path.join(path, project["guis"][0])
        self.open_gui(gui_filepath)

    def disable_gui(self, widget, recursive=True):
        """Disablds the widget.
        
        Args:
            
            widget: The widget to disable
            
            recursive: Wether to disable the children of the widget, or not.
        """
        widget.real_widget.setEnabled(False)
        if not recursive or not hasattr(widget, "children"):
            return
        for child in widget.children:
            self.disable_gui(child, True)

          
    def open_gui(self, filename):
        """Open a gui file
        
        Args:
        
            filename: The path to the file
        """
        try:
            gui = pychan.loadXML(filename)
            self.disable_gui(gui)
            self.clear_gui()
            self._filename = filename
            self._edit_window.addChild(gui)
            self._edit_window.adaptLayout()
            self._edit_wrapper.content = self._edit_window
        except IOError:
            self.error_dialog (u"File '%s' was not found." % 
                               (filename))
        except SAXParseException:
            self.error_dialog(u"Could not parse XML")
        except GuiXMLError, error:
            self.error_dialog(unicode(error))
            
        
    def createListener(self):
        self._listener = EditorEventListener(self)
        return self._listener

    def on_widget_dragged(self, event, widget):
        if self._marker_dragged:
            return
        if self._selected_widget is None:
            return
        rel_x = event.getX() - self._old_x
        rel_y = event.getY() - self._old_y
        self._selected_widget.x += rel_x
        self._selected_widget.y += rel_y
        self.position_markers()
        self._old_x = event.getX()
        self._old_y = event.getY()
        self._widget_dragged = True
