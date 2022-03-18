class Polyp:
    def __init__(self, ti, patches):
        self.ti = ti
        self.patches = patches
    
    def run(self):
        return False

    def get_patches(self):
        return self.patches