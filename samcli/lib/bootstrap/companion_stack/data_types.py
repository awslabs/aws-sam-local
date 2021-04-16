"""
    Date type classes for companion stacks
"""
import re
from typing import Optional
from samcli.lib.utils.hash import str_checksum


class CompanionStack:
    """
    Abstraction class for the companion stack
    Companion stack name will be generated by this class.
    """

    _parent_stack_name: str
    _escaped_parent_stack_name: str
    _parent_stack_hash: str
    _stack_name: str

    def __init__(self, parent_stack_name: str) -> None:
        self._parent_stack_name = parent_stack_name
        self._escaped_parent_stack_name = re.sub(r"[^a-z0-9]", "", self._parent_stack_name.lower())
        self._parent_stack_hash = str_checksum(self._parent_stack_name)
        self._stack_name = f"{self._parent_stack_name[:104]}-{self._parent_stack_hash[:8]}-CompanionStack"

    @property
    def parent_stack_name(self) -> str:
        """
        Parent stack name
        """
        return self._parent_stack_name

    @property
    def escaped_parent_stack_name(self) -> str:
        """
        Parent stack name with only alpha numerica characters
        """
        return self._escaped_parent_stack_name

    @property
    def parent_stack_hash(self) -> str:
        """
        MD5 hash of parent stack name
        """
        return self._parent_stack_hash

    @property
    def stack_name(self) -> str:
        """
        Companion stack stack name
        """
        return self._stack_name


class ECRRepo:
    """
    Abstraction class for ECR repos in companion stacks
    Logical ID, Physical ID, and Repo URI will be generated with this class.
    """

    _function_logical_id: Optional[str]
    _escaped_function_logical_id: Optional[str]
    _function_md5: Optional[str]
    _companion_stack: Optional[CompanionStack]
    _logical_id: Optional[str]
    _physical_id: Optional[str]
    _output_logical_id: Optional[str]

    def __init__(
        self,
        companion_stack: Optional[CompanionStack] = None,
        function_logical_id: Optional[str] = None,
        logical_id: Optional[str] = None,
        physical_id: Optional[str] = None,
        output_logical_id: Optional[str] = None,
    ):
        """
        Must be specified either with
        companion_stack and function_logical_id
        or
        logical_id, physical_id, and output_logical_id
        """
        self._function_logical_id = function_logical_id
        self._escaped_function_logical_id = (
            re.sub(r"[^a-z0-9]", "", self._function_logical_id.lower())
            if self._function_logical_id is not None
            else None
        )
        self._function_md5 = str_checksum(self._function_logical_id) if self._function_logical_id is not None else None
        self._companion_stack = companion_stack

        self._logical_id = logical_id
        self._physical_id = physical_id
        self._output_logical_id = output_logical_id

    @property
    def logical_id(self) -> Optional[str]:
        if self._logical_id is None and self._function_logical_id and self._function_md5:
            self._logical_id = self._function_logical_id[:52] + self._function_md5[:8] + "Repo"
        return self._logical_id

    @property
    def physical_id(self) -> Optional[str]:
        if (
            self._physical_id is None
            and self._companion_stack
            and self._function_md5
            and self._escaped_function_logical_id
        ):
            self._physical_id = (
                self._companion_stack.escaped_parent_stack_name
                + self._companion_stack.parent_stack_hash[:8]
                + "/"
                + self._escaped_function_logical_id
                + self._function_md5[:8]
                + "repo"
            )
        return self._physical_id

    @property
    def output_logical_id(self) -> Optional[str]:
        if self._output_logical_id is None and self._function_logical_id and self._function_md5:
            self._output_logical_id = self._function_logical_id[:52] + self._function_md5[:8] + "Out"
        return self._output_logical_id

    def get_repo_uri(self, account_id, region) -> str:
        return f"{account_id}.dkr.ecr.{region}.amazonaws.com/{self.physical_id}"
