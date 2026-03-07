import builtins

class PaletteArgb():
	def __init__(self, filename = ""):
		self.size = 0
		self.colors = []
		self.filename = filename
		if filename != "":
			file = builtins.open(filename, 'rb')
			file.read(22)
			self.size = int.from_bytes(file.read(2), byteorder='little', signed=True)
			for i in range(self.size):
				color = []
				for c in range(3):
					color.append(float(int.from_bytes(file.read(1), byteorder='little', signed=False))/255.0)
				file.read(1)
				self.colors.append(color)
			file.close
