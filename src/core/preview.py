"""Mesh preview generation with thumbnails and 3D renders."""
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
import io
import base64


class PreviewGenerator:
    """Generate preview images and thumbnails for mesh files."""

    def __init__(
        self,
        default_size: Tuple[int, int] = (512, 512),
        thumbnail_size: Tuple[int, int] = (128, 128)
    ):
        """Initialize preview generator.

        Args:
            default_size: Default preview image size
            thumbnail_size: Thumbnail size
        """
        self.default_size = default_size
        self.thumbnail_size = thumbnail_size

    def generate_preview(
        self,
        mesh: trimesh.Trimesh,
        size: Optional[Tuple[int, int]] = None,
        view_angle: Optional[Tuple[float, float, float]] = None,
        background: str = "white",
        show_axes: bool = False,
        show_grid: bool = True
    ) -> Image.Image:
        """Generate preview image of mesh.

        Args:
            mesh: Trimesh object
            size: Image size (width, height)
            view_angle: Camera view angle (azimuth, elevation, roll)
            background: Background color
            show_axes: Show coordinate axes
            show_grid: Show grid

        Returns:
            PIL Image object
        """
        size = size or self.default_size

        # Create scene
        scene = mesh.scene()

        # Set view angle
        if view_angle:
            angles = np.radians(view_angle)
            scene.set_camera(angles=angles)
        else:
            # Default isometric view
            scene.set_camera(angles=[np.pi/6, np.pi/4, 0])

        # Render to image
        try:
            # Get PNG data
            png_data = scene.save_image(resolution=size, visible=True)

            # Convert to PIL Image
            image = Image.open(io.BytesIO(png_data))

            # Add grid if requested
            if show_grid:
                image = self._add_grid(image)

            # Add axes if requested
            if show_axes:
                image = self._add_axes(image)

            return image

        except Exception as e:
            # Fallback to simple rendering
            return self._create_fallback_preview(mesh, size)

    def generate_thumbnail(
        self,
        mesh: trimesh.Trimesh,
        size: Optional[Tuple[int, int]] = None
    ) -> Image.Image:
        """Generate thumbnail image of mesh.

        Args:
            mesh: Trimesh object
            size: Thumbnail size

        Returns:
            PIL Image thumbnail
        """
        size = size or self.thumbnail_size

        # Generate full preview first
        preview = self.generate_preview(mesh, size=(512, 512))

        # Resize to thumbnail
        thumbnail = preview.resize(size, Image.Resampling.LANCZOS)

        return thumbnail

    def generate_multi_view(
        self,
        mesh: trimesh.Trimesh,
        views: List[str] = None,
        size: Tuple[int, int] = (256, 256)
    ) -> Dict[str, Image.Image]:
        """Generate multiple view angles of mesh.

        Args:
            mesh: Trimesh object
            views: List of view names (front, back, top, bottom, left, right)
            size: Size for each view

        Returns:
            Dictionary of view_name: Image
        """
        if views is None:
            views = ["front", "back", "top", "bottom", "left", "right"]

        view_angles = {
            "front": (0, 0, 0),
            "back": (180, 0, 0),
            "top": (0, 90, 0),
            "bottom": (0, -90, 0),
            "left": (90, 0, 0),
            "right": (-90, 0, 0),
            "isometric": (45, 35, 0)
        }

        results = {}
        for view_name in views:
            if view_name in view_angles:
                angle = view_angles[view_name]
                image = self.generate_preview(
                    mesh,
                    size=size,
                    view_angle=angle,
                    show_grid=False
                )
                results[view_name] = image

        return results

    def generate_contact_sheet(
        self,
        mesh: trimesh.Trimesh,
        views: List[str] = None,
        grid_size: Tuple[int, int] = (3, 2),
        cell_size: Tuple[int, int] = (256, 256)
    ) -> Image.Image:
        """Generate contact sheet with multiple views.

        Args:
            mesh: Trimesh object
            views: List of view names
            grid_size: Grid layout (columns, rows)
            cell_size: Size of each cell

        Returns:
            Combined contact sheet image
        """
        # Generate views
        view_images = self.generate_multi_view(mesh, views, cell_size)

        # Calculate sheet size
        cols, rows = grid_size
        sheet_width = cols * cell_size[0]
        sheet_height = rows * cell_size[1]

        # Create contact sheet
        sheet = Image.new("RGB", (sheet_width, sheet_height), "white")

        # Place views
        for idx, (view_name, image) in enumerate(view_images.items()):
            if idx >= cols * rows:
                break

            row = idx // cols
            col = idx % cols
            x = col * cell_size[0]
            y = row * cell_size[1]

            sheet.paste(image, (x, y))

            # Add label
            self._add_label(sheet, view_name, (x, y + cell_size[1] - 30))

        return sheet

    def generate_animated_preview(
        self,
        mesh: trimesh.Trimesh,
        frames: int = 36,
        size: Tuple[int, int] = (512, 512),
        axis: str = "y"
    ) -> List[Image.Image]:
        """Generate frames for animated preview.

        Args:
            mesh: Trimesh object
            frames: Number of frames
            size: Frame size
            axis: Rotation axis (x, y, or z)

        Returns:
            List of PIL Images
        """
        images = []

        for i in range(frames):
            angle = (i / frames) * 360

            if axis == "x":
                view_angle = (angle, 0, 0)
            elif axis == "y":
                view_angle = (0, angle, 0)
            else:  # z
                view_angle = (0, 0, angle)

            image = self.generate_preview(
                mesh,
                size=size,
                view_angle=view_angle,
                show_grid=False
            )
            images.append(image)

        return images

    def save_animated_gif(
        self,
        images: List[Image.Image],
        output_path: Path,
        duration: int = 100,
        loop: int = 0
    ) -> None:
        """Save animated GIF from image frames.

        Args:
            images: List of PIL Images
            output_path: Output file path
            duration: Duration per frame in milliseconds
            loop: Number of loops (0 for infinite)
        """
        if not images:
            return

        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=loop
        )

    def generate_base64_preview(
        self,
        mesh: trimesh.Trimesh,
        size: Optional[Tuple[int, int]] = None,
        format: str = "PNG"
    ) -> str:
        """Generate base64-encoded preview image.

        Args:
            mesh: Trimesh object
            size: Image size
            format: Image format (PNG, JPEG)

        Returns:
            Base64-encoded image string
        """
        # Generate preview
        image = self.generate_preview(mesh, size)

        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)

        base64_data = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/{format.lower()};base64,{base64_data}"

    def _create_fallback_preview(
        self,
        mesh: trimesh.Trimesh,
        size: Tuple[int, int]
    ) -> Image.Image:
        """Create fallback preview when rendering fails.

        Args:
            mesh: Trimesh object
            size: Image size

        Returns:
            Fallback preview image
        """
        # Create blank image
        image = Image.new("RGB", size, "white")
        draw = ImageDraw.Draw(image)

        # Draw simple wireframe projection
        vertices = mesh.vertices
        faces = mesh.faces

        # Simple orthographic projection
        scale = min(size) * 0.8 / mesh.bounding_box.extents.max()
        center = np.array(size) / 2

        # Project vertices to 2D
        projected = vertices[:, :2] * scale + center

        # Draw edges
        for face in faces:
            points = projected[face]
            for i in range(3):
                p1 = tuple(points[i].astype(int))
                p2 = tuple(points[(i + 1) % 3].astype(int))
                draw.line([p1, p2], fill="gray", width=1)

        # Add info text
        text = f"Vertices: {len(vertices)}\nFaces: {len(faces)}"
        draw.text((10, 10), text, fill="black")

        return image

    def _add_grid(self, image: Image.Image, spacing: int = 50) -> Image.Image:
        """Add grid overlay to image.

        Args:
            image: Input image
            spacing: Grid spacing in pixels

        Returns:
            Image with grid
        """
        draw = ImageDraw.Draw(image)
        width, height = image.size

        # Draw vertical lines
        for x in range(0, width, spacing):
            draw.line([(x, 0), (x, height)], fill=(200, 200, 200, 128), width=1)

        # Draw horizontal lines
        for y in range(0, height, spacing):
            draw.line([(0, y), (width, y)], fill=(200, 200, 200, 128), width=1)

        return image

    def _add_axes(self, image: Image.Image) -> Image.Image:
        """Add coordinate axes to image.

        Args:
            image: Input image

        Returns:
            Image with axes
        """
        draw = ImageDraw.Draw(image)
        width, height = image.size

        # Define axis origin (bottom-left corner)
        origin = (50, height - 50)
        axis_length = 40

        # X-axis (red)
        draw.line([origin, (origin[0] + axis_length, origin[1])],
                  fill=(255, 0, 0), width=2)
        draw.text((origin[0] + axis_length + 5, origin[1] - 5), "X",
                  fill=(255, 0, 0))

        # Y-axis (green)
        draw.line([origin, (origin[0], origin[1] - axis_length)],
                  fill=(0, 255, 0), width=2)
        draw.text((origin[0] - 10, origin[1] - axis_length - 10), "Y",
                  fill=(0, 255, 0))

        # Z-axis (blue) - diagonal for 3D effect
        z_end = (origin[0] + axis_length // 2, origin[1] - axis_length // 2)
        draw.line([origin, z_end], fill=(0, 0, 255), width=2)
        draw.text((z_end[0] + 5, z_end[1] - 5), "Z", fill=(0, 0, 255))

        return image

    def _add_label(
        self,
        image: Image.Image,
        text: str,
        position: Tuple[int, int]
    ) -> None:
        """Add text label to image.

        Args:
            image: Image to modify
            text: Label text
            position: Text position
        """
        draw = ImageDraw.Draw(image)

        # Draw background box
        text_bbox = draw.textbbox(position, text)
        padding = 5
        box = [
            text_bbox[0] - padding,
            text_bbox[1] - padding,
            text_bbox[2] + padding,
            text_bbox[3] + padding
        ]
        draw.rectangle(box, fill=(255, 255, 255, 200))

        # Draw text
        draw.text(position, text, fill="black")


class STLPreviewGenerator(PreviewGenerator):
    """Specialized preview generator for STL files."""

    def generate_from_file(
        self,
        file_path: Path,
        size: Optional[Tuple[int, int]] = None
    ) -> Optional[Image.Image]:
        """Generate preview directly from STL file.

        Args:
            file_path: Path to STL file
            size: Preview size

        Returns:
            Preview image or None if failed
        """
        try:
            mesh = trimesh.load(file_path)
            return self.generate_preview(mesh, size)
        except Exception as e:
            print(f"Failed to generate preview: {e}")
            return None

    def generate_info_overlay(
        self,
        mesh: trimesh.Trimesh,
        image: Image.Image
    ) -> Image.Image:
        """Add mesh information overlay to preview.

        Args:
            mesh: Trimesh object
            image: Preview image

        Returns:
            Image with info overlay
        """
        draw = ImageDraw.Draw(image)

        # Gather mesh info
        info = [
            f"Vertices: {len(mesh.vertices):,}",
            f"Faces: {len(mesh.faces):,}",
            f"Volume: {mesh.volume:.2f} mm³",
            f"Surface: {mesh.area:.2f} mm²"
        ]

        # Get bounding box
        bbox = mesh.bounding_box.extents
        info.append(f"Size: {bbox[0]:.1f} × {bbox[1]:.1f} × {bbox[2]:.1f} mm")

        # Draw info box
        y_offset = 10
        for line in info:
            draw.text((10, y_offset), line, fill="black")
            y_offset += 20

        return image