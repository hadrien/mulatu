from ${package_name}._base import BaseClient
from ${package_name}._resources import (
% for resource in root.resources.values():
    ${resource.class_name},
%endfor
)


__all__ = ["Client"]

class Client(BaseClient):
% for resource in root.resources.values():
    @property
    def ${resource.safe_name}(self) -> ${resource.class_name}:
        return ${resource.class_name}(self, {})
% endfor