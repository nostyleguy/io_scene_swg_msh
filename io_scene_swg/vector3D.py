# MIT License
#
# Copyright (c) 2022 Nick Rafalski
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class Vector3D(object):
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    def __neg__(self):
        return Vector3D(-self.x, -self.y, -self.z)
    def __add__(self, b):
        return Vector3D(self.x + b.x, self.y + b.y, self.z + b.z)
    def __sub__(self, b):
        return Vector3D(self.x - b.x, self.y - b.y, self.z - b.z)
    @staticmethod
    def dot(first, second):
        rx = first.x + second.x
        ry = first.y + second.y
        rz = first.z + second.z
        return rx + ry + rz
    @staticmethod
    def cross(first, second):
        return Vector3D((first.y * second.z) - (first.z * second.y),\
                        (first.z * second.x) - (first.x * second.z),\
                        (first.x * second.y) - (first.y * second.x)) 
    def __str__(self):
        return f'({self.x},{self.y},{self.z})'

def _calcSurfaceNormal(verts):
    result_normal = Vector3D(0.0, 0.0, 0.0)
    for i in range(len(verts)):
        current = verts[i]
        next = verts[(i+1)%len(verts)]
        result_normal.x += ((current.y - next.y) * (current.z + next.z))
        result_normal.y += ((current.z - next.z) * (current.x + next.x))
        result_normal.z += ((current.x - next.x) * (current.y + next.y))
    return result_normal