# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Widgets package for camera management UI components."""

from .resolution_widget import ResolutionWidget
from .status_bar import StatusBarWidget
from .log_panel import LogPanelWidget
from .camera_panel import CameraPanelWidget, CameraPanelCallbacks

__all__ = [
    "ResolutionWidget",
    "StatusBarWidget",
    "LogPanelWidget",
    "CameraPanelWidget",
    "CameraPanelCallbacks",
]
