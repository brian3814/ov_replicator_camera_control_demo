# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class CaptureStatus(Enum):
    """Status of the capture process."""
    STOPPED = "Stopped"
    CAPTURING = "Capturing"
    ERROR = "Error"


@dataclass
class CameraSettings:
    """Settings for a single camera in the capture list."""
    prim_path: str
    display_name: str
    width: int = 640
    height: int = 480
    interval_frames: int = 60
    enabled: bool = True
    output_rgb: bool = True
    last_capture_path: Optional[str] = None
    frame_counter: int = 0


@dataclass
class GlobalSettings:
    """Global capture settings."""
    output_folder: str = ""
    status: CaptureStatus = field(default=CaptureStatus.STOPPED)
