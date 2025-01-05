#!/usr/bin/python3
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################
import contextlib
import io
import tempfile
from enum import IntEnum
from typing import Protocol, Type, TypeVar

import atheris


class HasMax(Protocol):
    MAX: int


T = TypeVar("T", bound=IntEnum)


class EnhancedFuzzedDataProvider(atheris.FuzzedDataProvider):
    def ConsumeRandomBytes(self) -> bytes:
        return self.ConsumeBytes(self.ConsumeIntInRange(0, self.remaining_bytes()))

    def ConsumeRandomString(self) -> str:
        return self.ConsumeUnicodeNoSurrogates(
            self.ConsumeIntInRange(0, self.remaining_bytes())
        )

    def ConsumeRemainingString(self) -> str:
        return self.ConsumeUnicodeNoSurrogates(self.remaining_bytes())

    def ConsumeRemainingBytes(self) -> bytes:
        return self.ConsumeBytes(self.remaining_bytes())

    @contextlib.contextmanager
    def ConsumeMemoryFile(
        self, all_data: bool = False, as_bytes: bool = True
    ) -> io.BytesIO:
        if all_data:
            file_data = (
                self.ConsumeRemainingBytes()
                if as_bytes
                else self.ConsumeRemainingString()
            )
        else:
            file_data = (
                self.ConsumeRandomBytes() if as_bytes else self.ConsumeRandomString()
            )

        file = io.BytesIO(file_data) if as_bytes else io.StringIO(file_data)
        yield file
        file.close()

    @contextlib.contextmanager
    def ConsumeTemporaryFile(
        self, suffix: str, all_data: bool = False, as_bytes: bool = True
    ) -> str:
        if all_data:
            file_data = (
                self.ConsumeRemainingBytes()
                if as_bytes
                else self.ConsumeRemainingString()
            )
        else:
            file_data = (
                self.ConsumeRandomBytes() if as_bytes else self.ConsumeRandomString()
            )

        mode = "w+b" if as_bytes else "w+"
        tfile = tempfile.NamedTemporaryFile(mode=mode, suffix=suffix)
        tfile.write(file_data)
        tfile.seek(0)
        tfile.flush()
        yield tfile.name
        tfile.close()

    def ConsumeEnum(self, enum_type: Type[T]) -> T:
        return enum_type(self.ConsumeIntInRange(0, enum_type.MAX))
