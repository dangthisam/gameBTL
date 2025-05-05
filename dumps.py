import struct
import types
import sys

# Định nghĩa một số mã protocol
NONE = b'N'       # None
INT = b'I'        # Integer
FLOAT = b'F'      # Float
STR = b'S'        # String
LIST = b'L'       # List
DICT = b'D'       # Dictionary
TUPLE = b'T'      # Tuple
BOOL = b'B'       # Boolean
STOP = b'.'       # Kết thúc object

class CustomPickler:
    def __init__(self, protocol=None):
        self.protocol = protocol  # Chúng ta không thực sự sử dụng protocol ở đây
        self.memo = {}  # Để xử lý các tham chiếu lặp lại
        
    def dump_none(self, obj):
        return NONE
    
    def dump_bool(self, obj):
        if obj:
            return BOOL + b'\x01'
        return BOOL + b'\x00'
    
    def dump_int(self, obj):
        # Chuyển đổi số nguyên thành chuỗi byte
        return INT + str(obj).encode('utf-8') + b'\n'
    
    def dump_float(self, obj):
        # Chuyển đổi số thực thành chuỗi byte
        return FLOAT + str(obj).encode('utf-8') + b'\n'
    
    def dump_str(self, obj):
        # Chuyển đổi chuỗi thành chuỗi byte
        encoded = obj.encode('utf-8')
        return STR + struct.pack('!i', len(encoded)) + encoded
    
    def dump_list(self, obj):
        # Đánh dấu bắt đầu danh sách
        result = LIST + struct.pack('!i', len(obj))
        
        # Chuyển đổi từng phần tử trong danh sách
        for item in obj:
            result += self.dumps(item)
        
        # Đánh dấu kết thúc danh sách
        result += STOP
        return result
    
    def dump_dict(self, obj):
        # Đánh dấu bắt đầu từ điển
        result = DICT + struct.pack('!i', len(obj))
        
        # Chuyển đổi từng cặp khóa-giá trị trong từ điển
        for key, value in obj.items():
            result += self.dumps(key)
            result += self.dumps(value)
        
        # Đánh dấu kết thúc từ điển
        result += STOP
        return result
    
    def dump_tuple(self, obj):
        # Đánh dấu bắt đầu tuple
        result = TUPLE + struct.pack('!i', len(obj))
        
        # Chuyển đổi từng phần tử trong tuple
        for item in obj:
            result += self.dumps(item)
        
        # Đánh dấu kết thúc tuple
        result += STOP
        return result
    
    def dumps(self, obj):
        # Ánh xạ kiểu dữ liệu Python với các phương thức dump tương ứng
        type_dispatcher = {
            type(None): self.dump_none,
            bool: self.dump_bool,
            int: self.dump_int,
            float: self.dump_float,
            str: self.dump_str,
            list: self.dump_list,
            dict: self.dump_dict,
            tuple: self.dump_tuple,
        }
        
        # Lấy phương thức dump thích hợp
        dumper = type_dispatcher.get(type(obj))
        if dumper:
            return dumper(obj)
        else:
            raise TypeError(f"Cannot serialize object of type {type(obj)}")

def dumps(obj, protocol=None):
    """
    Serialize object hierarchy to bytes object.
    
    Parameters:
    - obj: Python object to be serialized
    - protocol: Optional protocol version (not fully implemented)
    
    Returns:
    - Bytes representation of the object
    """
    pickler = CustomPickler(protocol)
    return pickler.dumps(obj)

def loads(data):
    """
    Deserialize bytes to a Python object hierarchy.
    
    Parameters:
    - data: Bytes serialized using dumps()
    
    Returns:
    - Reconstructed Python object
    """
    # Xây dựng một unpickler đơn giản để đọc dữ liệu đã được pickle
    class CustomUnpickler:
        def __init__(self, data):
            self.data = data
            self.pos = 0
            
        def read_byte(self):
            b = self.data[self.pos:self.pos+1]
            self.pos += 1
            return b
            
        def read_int(self):
            # Đọc cho đến khi gặp '\n'
            start = self.pos
            while self.data[self.pos:self.pos+1] != b'\n':
                self.pos += 1
            val = int(self.data[start:self.pos].decode('utf-8'))
            self.pos += 1  # skip '\n'
            return val
            
        def read_float(self):
            # Đọc cho đến khi gặp '\n'
            start = self.pos
            while self.data[self.pos:self.pos+1] != b'\n':
                self.pos += 1
            val = float(self.data[start:self.pos].decode('utf-8'))
            self.pos += 1  # skip '\n'
            return val
            
        def read_str(self):
            # Đọc độ dài chuỗi
            size = struct.unpack('!i', self.data[self.pos:self.pos+4])[0]
            self.pos += 4
            
            # Đọc chuỗi với độ dài đã biết
            s = self.data[self.pos:self.pos+size].decode('utf-8')
            self.pos += size
            return s
            
        def read_size(self):
            # Đọc kích thước của danh sách/từ điển
            size = struct.unpack('!i', self.data[self.pos:self.pos+4])[0]
            self.pos += 4
            return size
            
        def load(self):
            b = self.read_byte()
            
            if b == NONE:
                return None
            elif b == BOOL:
                val = self.data[self.pos:self.pos+1]
                self.pos += 1
                return val == b'\x01'
            elif b == INT:
                return self.read_int()
            elif b == FLOAT:
                return self.read_float()
            elif b == STR:
                return self.read_str()
            elif b == LIST:
                size = self.read_size()
                result = []
                for _ in range(size):
                    result.append(self.load())
                if self.read_byte() != STOP:
                    raise ValueError("Expected STOP marker after list")
                return result
            elif b == TUPLE:
                size = self.read_size()
                result = []
                for _ in range(size):
                    result.append(self.load())
                if self.read_byte() != STOP:
                    raise ValueError("Expected STOP marker after tuple")
                return tuple(result)
            elif b == DICT:
                size = self.read_size()
                result = {}
                for _ in range(size):
                    key = self.load()
                    value = self.load()
                    result[key] = value
                if self.read_byte() != STOP:
                    raise ValueError("Expected STOP marker after dict")
                return result
            else:
                raise ValueError(f"Unknown object type marker: {b}")
    
    unpickler = CustomUnpickler(data)
    return unpickler.load()

# Ví dụ sử dụng
if __name__ == "__main__":
    # Serialize vài đối tượng khác nhau
    test_objects = [
        None,
        True, False,
        42, -10, 
        3.14159, -2.718,
        "Hello, world!", "String với Unicode: 你好世界",
        [1, 2, 3, 4],
        {"name": "John", "age": 30, "is_student": False},
        (1, "two", 3.0),
        ["nested", ["list", 1, 2], {"a": 1}],
        {"complex": {"nested": {"dictionary": [1, 2, 3]}}}
    ]
    
    # Kiểm tra serialize và deserialize
    for obj in test_objects:
        # Pickle đối tượng
        pickled = dumps(obj)
        print(f"Pickled {type(obj)}: {pickled[:20]}... ({len(pickled)} bytes)")
        
        # Unpickle và so sánh
        unpickled = loads(pickled)
        print(f"Unpickled: {unpickled}")
        print(f"Equal to original: {obj == unpickled}")
        print("-" * 40)