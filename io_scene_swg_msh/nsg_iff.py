import struct, io, builtins, os

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

        if filename != "":
            self.open_file(filename)
        else:
            self.length = initial_size
            self.data = bytearray(initial_size)
            s = StackFrame(0, 0, 0)
            self.stack.append(s)


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

    def read_tag(self):
        # byte[] tag_bytes = new byte[4];
        # read_misc(ref tag_bytes, 4);
        # EndianSwap(ref tag_bytes);
        # return Encoding.Default.GetString(tag_bytes)
        pass

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
        return self.read_misc(1) != 0

    def read_int32(self):
        return int.from_bytes(self.read_misc(4), byteorder='little', signed=True)

    def read_uint32(self):
        return int.from_bytes(self.read_misc(4), byteorder='little', signed=False)

    def read_int16(self):
        return int.from_bytes(self.read_misc(2), byteorder='little', signed=True)

    def read_uint16(self):
        return int.from_bytes(self.read_misc(2), byteorder='little', signed=False)

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

    def adjustDataAsNeeded(self, size):
        
        #// calculate the final required size of the data array
        neededLength = self.stack[0].length + size

        #print(f'Current: {self.stack[0].length} Needed: {neededLength}')

        #//NOT_NULL(data);
        #//IFF_DEBUG_FATAL(neededLength < 0, ("data size underflow"));

        #// check if we need to expand the data array
        if neededLength > self.stack[0].length:
            length = len(self.data)
            newLength = 1

            #// make sure the iff was growable
            #//DEBUG_FATAL(!growable, ("data size overflow %d/%d", neededLength, length));
            #//DEBUG_FATAL(length < 0, ("current length negative %d\n", length));

            #// handle when the iff is created with an initial size of 0, this fixes
            #// an infinite looping problem
            if len(self.data) <= 0:
                length = 1

            #// double in size until it supports the needed length
            # for (newLength = length * 2; newLength < neededLength; newLength *= 2)
            #     ;
            while newLength < neededLength:
                newLength *= 2

            #print(f"Need: {neededLength} was {len(self.data)} New {newLength}")
            #// allocate the new memory
            #//DEBUG_FATAL(newLength < 0, ("negative array allocation"));
            newData = bytearray(newLength)
            #//NOT_NULL(newData);

            #// copy the old data over to the new data
            #Array.Copy(data, newData, stack[0].length);
            newData[0:len(self.data)] = self.data

            #// replace the old data with the new data
            #data = null;
            self.data = newData
            #length = newLength;
        else:
            print(f'Required length: {neededLength} is met by current length: {len(self.data)}')

        #// move data around to either make room or remove data
        offset = self.stack[self.stack_depth].start + self.stack[self.stack_depth].used
        lengthToEnd = self.stack[0].length - offset
        if (size > 0):
            #Array.Copy(data, offset, data, offset + size, lengthToEnd);
            temp = self.data[offset:(offset + lengthToEnd)]
            self.data[offset+size:(offset+size+lengthToEnd)] = temp
        else:
            #Array.Copy(data, offset - size, data, offset, lengthToEnd + size);
            temp = self.data[offset-size:offset+lengthToEnd]
            self.data[offset:offset+lengthToEnd+size] = temp

        #// make sure all the enclosing stack entries know about the changed size
        i = 0
        while i <= self.stack_depth:
            #// update the stack's idea of the block length
            s = self.stack[i]
            s.length = s.length + size
            self.stack[i] = s
            #print(f'Stack now: {str(self.stack)}')
            #// the length of level 0 is the file size, so we should not write it
            if i != 0:
                #// update the data's idea of the block length
                if (i == self.stack_depth) and self.inChunk:
                    #//int ui32 = static_cast<int>(htonl(static_cast < unsigned long > (stack[i].length)));
                    size_bytes = int.to_bytes(self.stack[i].length, 4, byteorder="big", signed=False)
                    
                    #Array.Copy(ui32, 0, data, stack[i].start - 4, 4);
                    self.data[self.stack[i].start - 4:self.stack[i].start] = size_bytes
                    #//memcpy(data + stack[i].start - sizeof(uint32), &ui32, sizeof(uint32));
                
                else:
                    #// account for forms start beyond the first 4 data bytes, which is their real form name
                    #//const int ui32 = static_cast<int>(htonl(static_cast < unsigned long > (stack[i].length) + sizeof(Tag)));
                    #byte[] ui32 = ToBytes(stack[i].length + 4);
                    #EndianSwap(ref ui32);
                    size_bytes = int.to_bytes(self.stack[i].length + 4, 4, byteorder='big', signed=False)
                    #//Debug.LogFormat("Copying from: Start: {0} minus 8: {1}", stack[i].start, stack[i].start - 8);
                    #Array.Copy(ui32, 0, data, stack[i].start - 8, 4);
                    self.data[self.stack[i].start - 8:self.stack[i].start - 4] = size_bytes
                    #//memcpy(data + stack[i].start - sizeof(Tag) - sizeof(uint32), &ui32, sizeof(uint32));
            i += 1

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

    def insertFloatVector3(self, vec):
        self.insertFloat(vec[0])
        self.insertFloat(vec[1])
        self.insertFloat(vec[2])

    def insertFloatVector2(self, vec):
        self.insertFloat(vec[0])
        self.insertFloat(vec[1])

    def insert_int16(self, i):
        self.insertChunkData(int.to_bytes(i, 2, byteorder="little", signed=True))

    def insert_uint16(self, i):
        self.insertChunkData(int.to_bytes(i, 2, byteorder="little", signed=False))

    def insert_int32(self, i):
        self.insertChunkData(int.to_bytes(i, 4, byteorder="little", signed=True))

    def insert_uint32(self, i):
        self.insertChunkData(int.to_bytes(i, 4, byteorder="little", signed=False))

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

    def write(self, file_path):
        #print(f'self.length: {self.length} len(data): {len(self.data)} stack[0].length: {self.stack[0].length} stack[0].used: {self.stack[0].used}')
        f = builtins.open(file_path, 'wb')
        f.write(self.data[0:self.stack[0].length])
        f.close()



# iff = IFF(initial_size=0)
# print(str(iff.stack))
# iff.insertForm("MESH")
# iff.insertForm("0005")
# iff.insertForm("APPR")
# iff.insertChunk("TEST")
# iff.insertChunkString("This/is/a/string")
# iff.insertChunkString("Another One!!")
# iff.exitChunk("TEST")
# iff.insertChunk("ABCD")
# iff.insertFloat(1)
# iff.insertFloat(69)
# iff.exitChunk("ABCD")
# iff.exitForm()
# iff.insertForm("SPS ")
# iff.insertChunk("TEST")
# iff.insert_int32(2147483647)
# iff.exitChunk("TEST")
# iff.insertChunk("ABCD")
# iff.insert_int16(32767)
# iff.insert_int16(-32768)
# iff.exitChunk("ABCD")
# iff.exitForm()

# iff2 = IFF(initial_size=0)
# iff2.insertForm("NEW ")
# iff2.insertIff(iff)


# iff2.write("test2.iff")

# print(f'Bytes: {iff.data} Len: {len(iff.data)}')

# iff = IFF(filename="tie_advanced_l0.msh")
# print(iff.enterForm("MESH"))
# print(iff.enterForm("0005"))
# iff.enterForm("APPR")
# iff.exitForm()
# iff.enterForm("SPS ")

# 711 -  Normal In: 0.6141982078552246,-0.7461375594139099,0.25698116421699524