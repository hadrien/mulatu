from ._base import Resource

% for resource in reversed(root.all_resources):
class ${resource.class_name}(Resource):
    _path: str = "${resource.path}"

    % if resource.has_pattern_child():
        <%
        child = resource.pattern_child
        %>

    def __getitem__(self, ${child.safe_name}: str) -> ${child.class_name}:
        path_parameters = {
            "${child.safe_name}": ${child.safe_name},
            **self._path_parameters,
        }
        return ${child.class_name}(self._client, path_parameters)

    % endif

    % for child in resource.resources.values():
        % if not child.is_pattern():

    @property
    def ${child.safe_name}(self) -> ${child.class_name}:
        return ${child.class_name}(self._client, self._path_parameters)

        % endif
    % endfor



% endfor