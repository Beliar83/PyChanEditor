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

"""A container that can be resized to fit its contents"""

from fife.extensions.pychan.widgets import Container, Widget


class EditContainer(Container):
    """A container that can be resized to fit its contents"""

    def get_most_bottom_right_position(self):
        """Returns the position that is the most bottom right

        Returns: A tuple with the position
        """
        right_pos = 0
        bottom_pos = 0
        for child in self.children:
            assert isinstance(child, Widget)
            child_right_pos = child.x + child.width
            child_bottom_pos = child.y + child.height
            right_pos = max(right_pos, child_right_pos)
            bottom_pos = max(bottom_pos, child_bottom_pos)
        return (right_pos + 10, bottom_pos + 10)

    def resize_to_content(self):
        """Resize the edit container to fit its contents but
        not smaller than the parent
        """
        width, height = self.get_most_bottom_right_position()
        self.width = max(width, self.parent.width)
        self.height = max(height, self.parent.width)
