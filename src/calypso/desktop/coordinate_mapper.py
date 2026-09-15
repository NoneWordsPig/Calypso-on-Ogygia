from dataclasses import dataclass
@dataclass(frozen=True)
class ScreenTransform:
    source_size: tuple[int,int]=(1312,816); world_size: tuple[int,int]=(2560,1600); actual_primary_physical: tuple[int,int]=(2560,1600); dpi: float=1.0
    def source_to_world(self,p): return (p[0]*self.world_size[0]/self.source_size[0],p[1]*self.world_size[1]/self.source_size[1])
    def world_to_source(self,p): return (p[0]*self.source_size[0]/self.world_size[0],p[1]*self.source_size[1]/self.world_size[1])
    def world_to_logical(self,p): return self.physical_to_logical(self.world_to_physical(p))
    def logical_to_world(self,p): return self.physical_to_world(self.logical_to_physical(p))
    def physical_to_logical(self,p): return (p[0]/self.dpi,p[1]/self.dpi)
    def logical_to_physical(self,p): return (p[0]*self.dpi,p[1]*self.dpi)
    def world_to_physical(self,p): return (p[0]*self.actual_primary_physical[0]/self.world_size[0], p[1]*self.actual_primary_physical[1]/self.world_size[1])
    def physical_to_world(self,p): return (p[0]*self.world_size[0]/self.actual_primary_physical[0], p[1]*self.world_size[1]/self.actual_primary_physical[1])
