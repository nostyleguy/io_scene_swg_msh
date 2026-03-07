import struct, io, builtins, os, sys
import time
import datetime
import numpy 

timesExpanded = 0
class StackFrame():
	def __init__(self, start, length, used):
		self.start = start
		self.length = length
		self.used = used

	def __str__(self):
		return f'Start: {self.start} Length: {self.length} Used: {self.used}'

	def __repr__(self):
		return self.__str__()


class IFF():

	def __init__(self, *, initial_size = 0, filename = ""):
		self.inChunk = False
		self.stack = []
		self.length = 0
		self.data = None
		self.stack_depth = 0
		self.in_chunk = False
		self.timesExpanded = 0
		self.filename = filename
		if filename != "":
			self.open_file(filename)
		else:
			self.length = initial_size
			self.data = bytearray(initial_size)
			#s = StackFrame(0, self.length, 0)
			s = StackFrame(0, 0, 0)
			self.stack.append(s)

		self.MAXINT= (2**31 - 1)
		self.crctable = [
			0x00000000, 0x04C11DB7, 0x09823B6E, 0x0D4326D9, 0x130476DC, 0x17C56B6B, 0x1A864DB2, 0x1E475005,
			0x2608EDB8, 0x22C9F00F, 0x2F8AD6D6, 0x2B4BCB61, 0x350C9B64, 0x31CD86D3, 0x3C8EA00A, 0x384FBDBD,
			0x4C11DB70, 0x48D0C6C7, 0x4593E01E, 0x4152FDA9, 0x5F15ADAC, 0x5BD4B01B, 0x569796C2, 0x52568B75,
			0x6A1936C8, 0x6ED82B7F, 0x639B0DA6, 0x675A1011, 0x791D4014, 0x7DDC5DA3, 0x709F7B7A, 0x745E66CD,
			0x9823B6E0, 0x9CE2AB57, 0x91A18D8E, 0x95609039, 0x8B27C03C, 0x8FE6DD8B, 0x82A5FB52, 0x8664E6E5,
			0xBE2B5B58, 0xBAEA46EF, 0xB7A96036, 0xB3687D81, 0xAD2F2D84, 0xA9EE3033, 0xA4AD16EA, 0xA06C0B5D,
			0xD4326D90, 0xD0F37027, 0xDDB056FE, 0xD9714B49, 0xC7361B4C, 0xC3F706FB, 0xCEB42022, 0xCA753D95,
			0xF23A8028, 0xF6FB9D9F, 0xFBB8BB46, 0xFF79A6F1, 0xE13EF6F4, 0xE5FFEB43, 0xE8BCCD9A, 0xEC7DD02D,
			0x34867077, 0x30476DC0, 0x3D044B19, 0x39C556AE, 0x278206AB, 0x23431B1C, 0x2E003DC5, 0x2AC12072,
			0x128E9DCF, 0x164F8078, 0x1B0CA6A1, 0x1FCDBB16, 0x018AEB13, 0x054BF6A4, 0x0808D07D, 0x0CC9CDCA,
			0x7897AB07, 0x7C56B6B0, 0x71159069, 0x75D48DDE, 0x6B93DDDB, 0x6F52C06C, 0x6211E6B5, 0x66D0FB02,
			0x5E9F46BF, 0x5A5E5B08, 0x571D7DD1, 0x53DC6066, 0x4D9B3063, 0x495A2DD4, 0x44190B0D, 0x40D816BA,
			0xACA5C697, 0xA864DB20, 0xA527FDF9, 0xA1E6E04E, 0xBFA1B04B, 0xBB60ADFC, 0xB6238B25, 0xB2E29692,
			0x8AAD2B2F, 0x8E6C3698, 0x832F1041, 0x87EE0DF6, 0x99A95DF3, 0x9D684044, 0x902B669D, 0x94EA7B2A,
			0xE0B41DE7, 0xE4750050, 0xE9362689, 0xEDF73B3E, 0xF3B06B3B, 0xF771768C, 0xFA325055, 0xFEF34DE2,
			0xC6BCF05F, 0xC27DEDE8, 0xCF3ECB31, 0xCBFFD686, 0xD5B88683, 0xD1799B34, 0xDC3ABDED, 0xD8FBA05A,
			0x690CE0EE, 0x6DCDFD59, 0x608EDB80, 0x644FC637, 0x7A089632, 0x7EC98B85, 0x738AAD5C, 0x774BB0EB,
			0x4F040D56, 0x4BC510E1, 0x46863638, 0x42472B8F, 0x5C007B8A, 0x58C1663D, 0x558240E4, 0x51435D53,
			0x251D3B9E, 0x21DC2629, 0x2C9F00F0, 0x285E1D47, 0x36194D42, 0x32D850F5, 0x3F9B762C, 0x3B5A6B9B,
			0x0315D626, 0x07D4CB91, 0x0A97ED48, 0x0E56F0FF, 0x1011A0FA, 0x14D0BD4D, 0x19939B94, 0x1D528623,
			0xF12F560E, 0xF5EE4BB9, 0xF8AD6D60, 0xFC6C70D7, 0xE22B20D2, 0xE6EA3D65, 0xEBA91BBC, 0xEF68060B,
			0xD727BBB6, 0xD3E6A601, 0xDEA580D8, 0xDA649D6F, 0xC423CD6A, 0xC0E2D0DD, 0xCDA1F604, 0xC960EBB3,
			0xBD3E8D7E, 0xB9FF90C9, 0xB4BCB610, 0xB07DABA7, 0xAE3AFBA2, 0xAAFBE615, 0xA7B8C0CC, 0xA379DD7B,
			0x9B3660C6, 0x9FF77D71, 0x92B45BA8, 0x9675461F, 0x8832161A, 0x8CF30BAD, 0x81B02D74, 0x857130C3,
			0x5D8A9099, 0x594B8D2E, 0x5408ABF7, 0x50C9B640, 0x4E8EE645, 0x4A4FFBF2, 0x470CDD2B, 0x43CDC09C,
			0x7B827D21, 0x7F436096, 0x7200464F, 0x76C15BF8, 0x68860BFD, 0x6C47164A, 0x61043093, 0x65C52D24,
			0x119B4BE9, 0x155A565E, 0x18197087, 0x1CD86D30, 0x029F3D35, 0x065E2082, 0x0B1D065B, 0x0FDC1BEC,
			0x3793A651, 0x3352BBE6, 0x3E119D3F, 0x3AD08088, 0x2497D08D, 0x2056CD3A, 0x2D15EBE3, 0x29D4F654,
			0xC5A92679, 0xC1683BCE, 0xCC2B1D17, 0xC8EA00A0, 0xD6AD50A5, 0xD26C4D12, 0xDF2F6BCB, 0xDBEE767C,
			0xE3A1CBC1, 0xE760D676, 0xEA23F0AF, 0xEEE2ED18, 0xF0A5BD1D, 0xF464A0AA, 0xF9278673, 0xFDE69BC4,
			0x89B8FD09, 0x8D79E0BE, 0x803AC667, 0x84FBDBD0, 0x9ABC8BD5, 0x9E7D9662, 0x933EB0BB, 0x97FFAD0C,
			0xAFB010B1, 0xAB710D06, 0xA6322BDF, 0xA2F33668, 0xBCB4666D, 0xB8757BDA, 0xB5365D03, 0xB1F740B4
		]


	def open_file(self, file_path, mode = 'rb'):
		source_stream = builtins.open(file_path, mode)
		self.data = source_stream.read()
		source_stream.close()

		self.length = len(self.data)
		s = StackFrame(0, len(self.data), 0)
		self.stack.append(s)

		#print(self.data)

	def getCurrentName(self):
		return self.getBlockName(self.stack_depth)

	def getBlockName(self, depth):
		if self.getFirstTag(depth) == "FORM":
			return self.getSecondTag(depth)
		else:
			return self.getFirstTag(depth)

	def getCurrentLength(self):
		return self.getLength(self.stack_depth)

	def isCurrentChunk(self):
		return (self.getFirstTag(self.stack_depth) != "FORM")

	def isCurrentForm(self):
		return (self.getFirstTag(self.stack_depth) == "FORM")

	def atEndOfForm(self):
		return self.stack[self.stack_depth].used == self.stack[self.stack_depth].length

	def getCurrentName(self):
		return self.getBlockName(self.stack_depth)

	def getFirstTag(self, depth):
		start = self.stack[depth].start + self.stack[depth].used
		return self.data[start:start+4].decode('ASCII')

	def getLength(self, depth, offset = 0):
		start = self.stack[depth].start + self.stack[depth].used + offset + 4
		return int.from_bytes(self.data[start:start+4], 'big')

	def getSecondTag(self, depth):
		start = self.stack[depth].start + self.stack[depth].used + 8
		return self.data[start:start+4].decode('ASCII') 

	def enterChunk(self, name, validateName = True, optional = True):
		if not self.inChunk and not self.atEndOfForm() and self.isCurrentChunk() and (not validateName or self.getFirstTag(self.stack_depth) == name):
			self.stack.append(StackFrame(self.stack[self.stack_depth].start +self.stack[self.stack_depth].used + 4 + 4, self.getLength(self.stack_depth), 0))

			#Debug.LogFormat("[EnterChunk: {4}] StackDepth: {0} Start: {1} Length: {2} Used: {3}", stackDepth, stack[stackDepth].start, stack[stackDepth].length, stack[stackDepth].used, getFirstTag(stackDepth));

			self.stack_depth += 1
			self.inChunk = True

			return True
		
		elif (validateName and (self.getSecondTag(self.stack_depth) != name)):
			print(f"[EnterChunk]: FORM Name: {self.getFirstTag(self.stack_depth)} doesnt match requested: {name}")

		return False
	def enterAnyForm(self):
		return self.enterForm("", False, False)

	def enterForm(self, name, validateName = True, optional = True):
		#print(f"Trying to enter form with: self.inChunk: {self.inChunk} self.atEndOfForm(): {self.atEndOfForm()} self.isCurrentForm(): {self.isCurrentForm()}")
		if not self.inChunk and not self.atEndOfForm() and self.isCurrentForm() and (not validateName or (self.getSecondTag(self.stack_depth) == name)):
			s = StackFrame(self.stack[self.stack_depth].start +self.stack[self.stack_depth].used + 4 + 4 + 4, self.getLength(self.stack_depth) - 4, 0)
			self.stack.append(s)
			#print(f'Stack now: {str(self.stack)}')
			#Debug.LogFormat("[EnterForm: {4}] StackDepth: {0} Start: {1} Length: {2} Used: {3}", stackDepth, stack[stackDepth].start, stack[stackDepth].length, stack[stackDepth].used, getSecondTag(stackDepth));

			self.stack_depth += 1
			return True
		elif validateName and (self.getSecondTag(self.stack_depth) != name):
			print(f"[EnterForm]: FORM Name: {self.getSecondTag(self.stack_depth)} doesn't match requested: {name}")
		else:
			print(f"Got to weird part of enterForm. self.inChunk: {self.inChunk} self.atEndOfForm(): {self.atEndOfForm()} self.isCurrentForm(): {self.isCurrentForm()}")

		return False	

	def exitForm(self, name = ""):
		if name != "" and self.getSecondTag(self.stack_depth - 1) != name:
			print(f"[ExitForm] Requested: {name} but found {self.getSecondTag(self.stack_depth - 1)}")
			return

		self.stack[self.stack_depth - 1].used += self.stack[self.stack_depth].length + 4 + 4 + 4
		#//Debug.LogFormat("[ExitForm: {4}] StackDepth: {0} Start: {1} Length: {2} Used: {3}", stackDepth, stack[stackDepth].start, stack[stackDepth].length, stack[stackDepth].used, getSecondTag(stackDepth));
		self.stack.pop()
		self.stack_depth -= 1
	def exitChunk(self, name):
		if self.getFirstTag(self.stack_depth - 1) != name:
			print(f"[ExitChunk] Requested: {self.getFirstTag(self.stack_depth - 1)} but found {name}")
			return

		self.stack[self.stack_depth - 1].used += self.stack[self.stack_depth].length + 4 + 4
		self.stack.pop()
		self.stack_depth -= 1
		self.inChunk = False

	def read_misc(self, readLength):
		s = self.stack[self.stack_depth]
		readData = self.data[s.start + s.used:s.start + s.used + readLength]
		s.used += readLength
		self.stack[self.stack_depth] = s
		return readData

	def read_bool8(self):
		return self.read_uint8() != 0

	def read_int8(self):
		return int.from_bytes(self.read_misc(1), byteorder='little', signed=True)

	def read_uint8(self):
		return int.from_bytes(self.read_misc(1), byteorder='little', signed=False)

	def read_int32(self):
		return int.from_bytes(self.read_misc(4), byteorder='little', signed=True)

	def read_uint32(self):
		return int.from_bytes(self.read_misc(4), byteorder='little', signed=False)

	def read_int16(self):
		return int.from_bytes(self.read_misc(2), byteorder='little', signed=True)

	def read_uint16(self):
		return int.from_bytes(self.read_misc(2), byteorder='little', signed=False)

	def read_color(self):
		return float(int.from_bytes(self.read_misc(1), byteorder='little', signed=False))/255.0

	def read_byte(self):
		return self.read_misc(1)

	def read_string(self):
		s = self.stack[self.stack_depth]
		pos = (s.start + s.used)
		end = self.data.find(b'\0', pos)
		if end != -1:
			s.used += (end - pos) + 1
			return self.data[pos:end].decode('ASCII')
		else:
			s.used = len(self.data) + 1 # definitely wrong, but shits broke anyway
			return self.data[pos:].decode('ASCII')

	def read_float(self):
		return struct.unpack('f', self.read_misc(4))[0]

	def read_vector3(self):
		return [self.read_float(), self.read_float(), self.read_float()]
	
	def read_vector4(self):
		return [self.read_float(), self.read_float(), self.read_float(), self.read_float()]
	
	def read_tag(self):
		tag = ""
		for i in range(4):
			tag += chr(self.read_uint8())
		return tag[::-1]
	
	def adjustDataAsNeeded(self, size):
		neededLength = self.stack[0].length + size

		# check if we need to expand the data array
		if neededLength > self.length:
			newLength = 0

			# handle when the iff is created with an initial size of 0, this fixes
			# an infinite looping problem
			if self.length <= 0:
				self.length = 1

			# double in size until it supports the needed length
			newLength = 2 * self.length
			while newLength < neededLength:
				newLength *= 2

			# allocate the new memory
			newData = bytearray(newLength)

			# copy the old data over to the new data
			newData[0:len(self.data)] = self.data

			# replace the old data with the new data
			self.data = newData
			self.length = newLength
			print(f"Grew data. Total: {len(self.data)} Needed: {str(neededLength)} NewLength: {str(newLength)} Stack length: {str(self.stack[0].length)} Times expanded: {str(self.timesExpanded)}" )
			self.timesExpanded +=1
		else:
			#print(f'Required length: {neededLength} is met by current length: {len(self.data)}')
			pass

		# move data around to either make room or remove data
		offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used
		lengthToEnd = self.stack[0].length - offset

		if size > 0:
			#memmove(data+offset+size, data+offset, lengthToEnd);
			temp = self.data[offset:(offset + lengthToEnd)]
			self.data[offset+size:(offset+size+lengthToEnd)] = temp
		else:
			#memmove(data+offset, data+offset-size, lengthToEnd+size);
			self.data=bytearray(self.data)
			temp = self.data[offset-size:offset+lengthToEnd]
			self.data[offset:offset+lengthToEnd+size] = bytearray(temp)

		#make sure all the enclosing stack entries know about the changed size
		for i in range(0, len(self.stack)):
			#update the stack's idea of the block length
			s = self.stack[i]
			s.length = s.length + size
			self.stack[i] = s

			# the length of level 0 is the file size, so we should not write it
			if i != 0:
				# update the data's idea of the block length
				if (i == self.stack_depth) and self.inChunk:
					#const int ui32 = static_cast<int>(htonl(static_cast<unsigned long>(stack[i].length)));
					size_bytes = int.to_bytes(self.stack[i].length, 4, byteorder="big", signed=False)
					#memcpy(data+stack[i].start-sizeof(uint32), &ui32, sizeof(uint32));
					self.data[self.stack[i].start - 4:self.stack[i].start] = size_bytes
				else:
					# account for forms start beyond the first 4 data bytes, which is their real form name
					#const int ui32 = static_cast<int>(htonl(static_cast<unsigned long>(stack[i].length) + sizeof(Tag)));
					size_bytes = int.to_bytes(self.stack[i].length + 4, 4, byteorder='big', signed=False)
					#memcpy(data+stack[i].start-sizeof(Tag)-sizeof(uint32), &ui32, sizeof(uint32));
					self.data[self.stack[i].start - 8:self.stack[i].start - 4] = size_bytes
   
			
	def insertForm(self, name, shouldEnterForm = True):
		FORM_OVERHEAD = 4 + 4 + 4

		if self.data == None:
			self.data = bytearray(FORM_OVERHEAD) 

		self.adjustDataAsNeeded(FORM_OVERHEAD)

		#// compute the offset to start inserting data at
		offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used

		#//Debug.LogFormat("Data Length: {0} Offset: {1}", data.Length, offset);

		#// add the form header
		t = "FORM".encode('ASCII')
		#Array.Copy(ToBytes(t, false), 0, data, offset, 4);
		self.data[offset:offset+4] = t
		offset += 4

		#// add the size of the form
		ui32 = 4
		sizeBytes = int.to_bytes(ui32, 4, byteorder='big', signed=False)
		#EndianSwap(ref sizeBytes);
		#Array.Copy(sizeBytes, 0, data, offset, 4);
		self.data[offset:offset+4] = sizeBytes

		offset += 4

		#// add the real form name
		t = name.encode('ASCII')
		self.data[offset:offset+4] = t

		#//// enter the form if requested
		if shouldEnterForm:
			#print(f'Next Form: {self.getCurrentName()}')
			if not self.enterAnyForm():
				print(f'Couldnt enter form: {self.getCurrentName()}')
	
	
	def insertNumberedForm(self, n, shouldEnterForm = True):
		s=str(n).zfill(4)
		self.insertForm(s, shouldEnterForm)

	def insertChunk(self, name, shouldEnterChunk = True):
		CHUNK_OVERHEAD = 4 + 4
		#// make sure the data array can handle this addition
		self.adjustDataAsNeeded(CHUNK_OVERHEAD)

		#// compute the offset to start inserting data at
		offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used

		#// add the form header
		t = name.encode('ASCII')
		self.data[offset:offset+4] = t
		offset += 4

		#// add the size of the form
		ui32 = 0
		sizeBytes = int.to_bytes(ui32, 4, byteorder='big', signed=False)
		self.data[offset:offset+4] = sizeBytes

		#// enter the chunk if requested
		if shouldEnterChunk:
			self.enterChunk(name)

	def insertChunkData(self, newData):
		if(len(newData) == 0):
			return
		self.adjustDataAsNeeded(len(newData))

		offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used

		self.data[offset:offset+len(newData)] = newData

		self.stack[self.stack_depth].used += len(newData)

	def insert_byte(self, b):
		self.insertChunkData(int.to_bytes(b, 1, byteorder="little", signed=False))

	def insert_bool(self, b):
		self.insert_byte(1 if b else 0)

	def insertChunkString(self, s, nullTerminate = True):
		self.insertChunkData(s.encode('ASCII'))
		if nullTerminate:
			self.insert_byte(0)

	def insertFloat(self, f):
		self.insertChunkData(struct.pack('f', f))
		
	def insertFloatVector4(self, vec):
		self.insertFloat(vec[0])
		self.insertFloat(vec[1])
		self.insertFloat(vec[2])
		self.insertFloat(vec[3])

	def insertFloatVector3(self, vec):
		self.insertFloat(vec[0])
		self.insertFloat(vec[1])
		self.insertFloat(vec[2])

	def insertFloatVector2(self, vec):
		self.insertFloat(vec[0])
		self.insertFloat(vec[1])

	def insert_int8(self, i):
		self.insertChunkData(int.to_bytes(i, 1, byteorder="little", signed=True))

	def insert_int16(self, i):
		self.insertChunkData(int.to_bytes(i, 2, byteorder="little", signed=True))

	def insert_uint16(self, i):
		self.insertChunkData(int.to_bytes(i, 2, byteorder="little", signed=False))

	def insert_int32(self, i):
		self.insertChunkData(int.to_bytes(i, 4, byteorder="little", signed=True))	

	def insertInt32Vector3(self, vec):
		self.insert_int32(vec[0])
		self.insert_int32(vec[1])
		self.insert_int32(vec[2])

	def insert_uint32(self, i):
		self.insertChunkData(int.to_bytes(i, 4, byteorder="little", signed=False))
	
	def insert_color(self, color):
		c = []
		for i in range(4):
			c.append(int(numpy.clip(color[i] * 255, 0, 255)))
		self.insert_byte(c[2])
		self.insert_byte(c[1])
		self.insert_byte(c[0])
		self.insert_byte(c[3])
		#print(f"ARGB: {c[3]}, {c[0]}, {c[1]}, {c[2]}")

	def insertIff(self, iff):
		#make sure the data array can handle this addition
		newLength=iff.stack[0].length
		self.adjustDataAsNeeded(newLength)

		#// compute the offset to start inserting data at
		offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used

		#// add the other iff
		#//memcpy(data+offset, iff->data, iff->stack[0].length);
		#Array.Copy(iff.data, 0, data, offset, iff.stack[0].length);
		self.data[offset:offset+newLength] = iff.data
		#// advance past the data
		self.stack[self.stack_depth].used += newLength

	def insertIffData(self, data):
		#make sure the data array can handle this addition
		newLength=len(data)
		self.adjustDataAsNeeded(newLength)

		#// compute the offset to start inserting data at
		offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used

		#// add the other iff
		#//memcpy(data+offset, iff->data, iff->stack[0].length);
		#Array.Copy(iff.data, 0, data, offset, iff.stack[0].length);
		self.data[offset:offset+newLength] = data
		#// advance past the data
		self.stack[self.stack_depth].used += newLength

	
	def deleteChunkData(self, dataLength):
		if not self.inChunk:
			print("Error. Tried to call deleteChunkData while not in chunk")
			return
		self.adjustDataAsNeeded(-dataLength)



	def seekWithinChunk(self, offset):
		self.stack[self.stack_depth].used += offset

	def update_int32(self, delta):
		value = self.read_int32()
		self.seekWithinChunk(-4)
		self.deleteChunkData(4)
		self.insert_int32(value + delta)
		return value + delta

	def update_float(self, delta):
		value = self.read_float()
		self.seekWithinChunk(-4)
		self.deleteChunkData(4)
		self.insertFloat(value + delta)
		return value + delta

	def update_vector3(self, dx, dy, dz):
		x = self.read_float()
		y = self.read_float()
		z = self.read_float()
		self.seekWithinChunk(-12)
		self.deleteChunkData(12)
		self.insertFloat(x+dx)
		self.insertFloat(y+dy)
		self.insertFloat(z+dz)
		return [x+dx, y+dy, z+dz]

	def write(self, file_path):
		#print(f'self.length: {self.length} len(data): {len(self.data)} stack[0].length: {self.stack[0].length} stack[0].used: {self.stack[0].used}')
		t = time.time()
		f = builtins.open(file_path, 'wb')
		f.write(self.data[0:self.stack[0].length])
		f.close()
		now = time.time() 
		#print("Writing data took: " + str(datetime.timedelta(seconds=(now - t))))

	def calculate(self):
		print(f'Max size: {self.MAXINT}')
		crc=0xFFFFFFFF
		for d in self.data:
			ind = self.int_overflow((crc>>24) ^ d) & 0xFF

			#uind = int.from_bytes(ind.to_bytes(4, 'little', signed=True), 'little', signed=False)
			temp = (self.crctable[ind] ^ (crc << 8))
			crc = self.int_overflow(temp)
			#print(f"{d}: Ind: {ind} Temp: {temp} CRC now {crc}")
		return crc

	def int_overflow(self, val):
		if not -self.MAXINT-1 <= val <= self.MAXINT:
			val = (val + (self.MAXINT + 1)) % (2 * (self.MAXINT + 1)) - self.MAXINT - 1
		return val

