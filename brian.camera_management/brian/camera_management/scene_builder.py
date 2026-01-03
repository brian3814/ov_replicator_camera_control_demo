"""Scene builder for creating sample scenes with objects and cameras."""

from typing import List, Tuple

import omni.replicator.core as rep
import omni.usd


__all__ = ["SceneBuilder"]


class SceneBuilder:
    """Utility class for creating sample scenes with objects and cameras."""

    # Track created prims for cleanup
    _created_prims: List[str] = []
    _created_camera_paths: List[str] = []
    _created_objects: List = []  # Store replicator node references for randomization

    # Default positions for objects (centered around origin)
    DEFAULT_OBJECT_POSITIONS = {
        "cube": (-100, 0, 0),
        "sphere": (0, 0, 0),
        "cone": (100, 0, 0),
    }

    # Default camera configurations (Z-up coordinate system)
    DEFAULT_CAMERAS = {
        "Camera_Front": {
            "position": (0, -500, 0),
            "look_at": (0, 0, 0),
            "description": "Front view at same Z height as objects",
        },
        "Camera_Isometric": {
            "position": (300, -300, 300),
            "look_at": (0, 0, 0),
            "description": "2.5D isometric angle view",
        },
        "Camera_Top": {
            "position": (0, 0, 500),
            "look_at": (0, 0, 0),
            "description": "Top-down view",
        },
    }

    @classmethod
    def create_sample_scene(cls) -> Tuple[bool, List[str]]:
        """Create a sample scene with basic objects, lighting, and demo cameras.

        Creates:
        - Three primitive objects (cube, sphere, cone) arranged in a row
        - A distant light for scene illumination
        - Three cameras positioned to view the objects from different angles

        Returns:
            Tuple of (success: bool, camera_paths: List[str])
        """
        try:
            # Check if stage exists
            context = omni.usd.get_context()
            stage = context.get_stage()
            if not stage:
                print("[brian.camera_management] No stage available")
                return False, []

            # Clear tracking lists for fresh creation
            cls._created_prims.clear()
            cls._created_camera_paths.clear()
            cls._created_objects.clear()

            # Create light
            cls._create_light()

            # Create objects
            cls._create_objects()

            # Create cameras
            cls._create_cameras()

            # Set up randomizers for object rotation
            cls._setup_randomizers()

            print("[brian.camera_management] Sample scene created successfully")
            return True, cls._created_camera_paths.copy()

        except Exception as e:
            print(f"[brian.camera_management] Error creating sample scene: {e}")
            return False, []

    @classmethod
    def _create_light(cls):
        """Create a distant light to illuminate the scene."""
        light = rep.create.light(
            rotation=(315, 0, 0),
            intensity=3000,
            light_type="distant",
            name="SampleLight"
        )
        # Track the light prim path
        light_prim = light.get_output_prims()["prims"][0]
        cls._created_prims.append(str(light_prim.GetPath()))
        print("[brian.camera_management] Created sample light")

    @classmethod
    def _create_objects(cls):
        """Create the sample primitive objects and track their prim paths."""
        # Create a cube on the left
        cube = rep.create.cube(
            position=cls.DEFAULT_OBJECT_POSITIONS["cube"],
            scale=50,
            semantics=[("class", "cube")],
            name="SampleCube"
        )
        cube_prim = cube.get_output_prims()["prims"][0]
        cls._created_prims.append(str(cube_prim.GetPath()))
        cls._created_objects.append(cube)

        # Create a sphere in the center
        sphere = rep.create.sphere(
            position=cls.DEFAULT_OBJECT_POSITIONS["sphere"],
            scale=50,
            semantics=[("class", "sphere")],
            name="SampleSphere"
        )
        sphere_prim = sphere.get_output_prims()["prims"][0]
        cls._created_prims.append(str(sphere_prim.GetPath()))
        cls._created_objects.append(sphere)

        # Create a cone on the right
        cone = rep.create.cone(
            position=cls.DEFAULT_OBJECT_POSITIONS["cone"],
            scale=50,
            semantics=[("class", "cone")],
            name="SampleCone"
        )
        cone_prim = cone.get_output_prims()["prims"][0]
        cls._created_prims.append(str(cone_prim.GetPath()))
        cls._created_objects.append(cone)

        print("[brian.camera_management] Created sample objects: cube, sphere, cone")

    @classmethod
    def _create_cameras(cls):
        """Create the demo cameras positioned to view the objects and track their paths."""
        for camera_name, config in cls.DEFAULT_CAMERAS.items():
            camera = rep.create.camera(
                position=config["position"],
                look_at=config["look_at"],
                name=camera_name
            )
            # Track camera prim paths
            camera_prim = camera.get_output_prims()["prims"][0]
            camera_path = str(camera_prim.GetPath())
            cls._created_prims.append(camera_path)
            cls._created_camera_paths.append(camera_path)
            print(f"[brian.camera_management] Created camera: {camera_name} - {config['description']}")

    @classmethod
    def _setup_randomizers(cls):
        """Set up randomizers to apply random rotation to objects on each replicator frame."""
        # Get sample objects by their semantic labels
        sample_objects = rep.get.prims(
            semantics=[("class", "cube"), ("class", "sphere"), ("class", "cone")]
        )

        # Set up trigger to randomize rotation on each frame
        with rep.trigger.on_frame():
            with sample_objects:
                rep.modify.pose(
                    rotation=rep.distribution.uniform(
                        (0, 0, 0),
                        (360, 360, 360)
                    )
                )

        print("[brian.camera_management] Set up random rotation for sample objects")

    @classmethod
    def clear_sample_scene(cls) -> bool:
        """Delete all prims created by create_sample_scene().

        Returns:
            True if cleanup was successful, False otherwise.
        """
        try:
            context = omni.usd.get_context()
            stage = context.get_stage()
            if not stage:
                print("[brian.camera_management] No stage available for cleanup")
                return False

            deleted_count = 0
            for prim_path in cls._created_prims:
                prim = stage.GetPrimAtPath(prim_path)
                if prim and prim.IsValid():
                    stage.RemovePrim(prim_path)
                    deleted_count += 1

            cls._created_prims.clear()
            cls._created_camera_paths.clear()
            cls._created_objects.clear()

            print(f"[brian.camera_management] Cleared {deleted_count} sample scene prims")
            return True

        except Exception as e:
            print(f"[brian.camera_management] Error clearing sample scene: {e}")
            return False

    @classmethod
    def get_created_camera_paths(cls) -> List[str]:
        """Get the list of camera paths created by the last create_sample_scene() call.

        Returns:
            List of camera prim path strings.
        """
        return cls._created_camera_paths.copy()

    @classmethod
    def get_camera_names(cls) -> list:
        """Get the list of default camera names.

        Returns:
            List of camera name strings.
        """
        return list(cls.DEFAULT_CAMERAS.keys())
