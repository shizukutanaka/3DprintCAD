"""React/Vue-inspired modern UI component system for 3D CAD applications."""

from __future__ import annotations

import json
import logging
import time
import weakref
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Type, TypeVar
from pathlib import Path
import re


T = TypeVar('T')


class ComponentLifecycle(Enum):
    """Component lifecycle states (React/Vue equivalent)."""
    CREATED = "created"
    MOUNTED = "mounted"
    UPDATED = "updated"
    UNMOUNTED = "unmounted"


class StateManagementType(Enum):
    """State management patterns."""
    LOCAL = "local"      # Component local state (Vue data)
    GLOBAL = "global"    # Global state (Redux/Vuex)
    SHARED = "shared"    # Shared between components (React Context)


@dataclass
class ComponentState:
    """Component state container (React state equivalent)."""
    data: Dict[str, Any] = field(default_factory=dict)
    computed: Dict[str, Callable] = field(default_factory=dict)
    watchers: Dict[str, Callable] = field(default_factory=dict)
    lifecycle: ComponentLifecycle = ComponentLifecycle.CREATED


@dataclass
class ComponentProps:
    """Component properties (React props equivalent)."""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: Dict[str, Callable] = field(default_factory=dict)
    children: List['UIComponent'] = field(default_factory=list)
    slots: Dict[str, Any] = field(default_factory=dict)  # Vue slots equivalent


@dataclass
class RenderContext:
    """Rendering context for components."""
    parent: Optional['UIComponent'] = None
    depth: int = 0
    theme: str = "default"
    locale: str = "en"
    responsive_breakpoints: Dict[str, int] = field(default_factory=lambda: {
        "mobile": 768,
        "tablet": 1024,
        "desktop": 1200
    })


class UIComponent:
    """React/Vue-inspired UI component base class."""

    def __init__(self, name: str, props: Optional[ComponentProps] = None):
        self.name = name
        self.props = props or ComponentProps()
        self.state = ComponentState()
        self.lifecycle = ComponentLifecycle.CREATED
        self.render_context = RenderContext()
        self.children: List[UIComponent] = []
        self.parent: Optional[UIComponent] = None
        self.dom_element: Optional[Any] = None
        self.logger = logging.getLogger(f"component.{name}")

        # React-style refs
        self.refs: Dict[str, Any] = {}

        # Event handlers (React/Vue equivalent)
        self.event_handlers: Dict[str, Callable] = {}

        # Lifecycle hooks (React/Vue equivalent)
        self.hooks = {
            "before_mount": [],
            "mounted": [],
            "before_update": [],
            "updated": [],
            "before_unmount": [],
            "unmounted": []
        }

    def set_state(self, new_state: Dict[str, Any]) -> None:
        """Set component state (React setState equivalent)."""
        old_state = self.state.data.copy()

        # Update state
        self.state.data.update(new_state)

        # Trigger watchers (Vue watch equivalent)
        for key, watcher in self.state.watchers.items():
            if key in new_state or key in old_state:
                old_value = old_state.get(key)
                new_value = self.state.data.get(key)
                if old_value != new_value:
                    try:
                        watcher(old_value, new_value)
                    except Exception as e:
                        self.logger.error(f"Watcher error for {key}: {e}")

        # Trigger update lifecycle
        self._trigger_lifecycle("before_update")
        self.render()
        self._trigger_lifecycle("updated")

    def computed_property(self, name: str, compute_func: Callable) -> Any:
        """Create computed property (Vue computed equivalent)."""
        self.state.computed[name] = compute_func
        return property(lambda self: compute_func())

    def watch(self, property_name: str, callback: Callable) -> None:
        """Watch property changes (Vue watch equivalent)."""
        self.state.watchers[property_name] = callback

    def add_lifecycle_hook(self, hook_name: str, callback: Callable) -> None:
        """Add lifecycle hook (React/Vue lifecycle methods)."""
        if hook_name in self.hooks:
            self.hooks[hook_name].append(callback)

    def _trigger_lifecycle(self, hook_name: str) -> None:
        """Trigger lifecycle hooks."""
        for hook in self.hooks.get(hook_name, []):
            try:
                hook()
            except Exception as e:
                self.logger.error(f"Lifecycle hook {hook_name} failed: {e}")

    def mount(self, parent_element: Any, context: Optional[RenderContext] = None) -> None:
        """Mount component (React componentDidMount equivalent)."""
        self.lifecycle = ComponentLifecycle.MOUNTED
        self.render_context = context or RenderContext()
        self.parent = None  # Top-level component

        self._trigger_lifecycle("before_mount")
        self.render()
        self._trigger_lifecycle("mounted")

    def unmount(self) -> None:
        """Unmount component (React componentWillUnmount equivalent)."""
        self._trigger_lifecycle("before_unmount")

        # Unmount children first
        for child in self.children:
            child.unmount()

        self.lifecycle = ComponentLifecycle.UNMOUNTED
        self._trigger_lifecycle("unmounted")

    def render(self) -> str:
        """Render component (React render equivalent)."""
        # This would generate HTML/JSX in a real React/Vue implementation
        # For now, return a template string
        template = self.get_template()
        return self._process_template(template)

    def get_template(self) -> str:
        """Get component template (React JSX/Vue template equivalent)."""
        # Override in subclasses
        return f"<div class='{self.name}'>Component template not implemented</div>"

    def _process_template(self, template: str) -> str:
        """Process template with data binding (Vue template compilation equivalent)."""
        # Simple template processing - in real implementation would use a template engine
        processed = template

        # Replace data bindings (Vue {{ }} syntax)
        for key, value in self.state.data.items():
            processed = processed.replace(f"{{{{ {key} }}}}", str(value))

        # Replace computed properties
        for key, compute_func in self.state.computed.items():
            try:
                value = compute_func()
                processed = processed.replace(f"{{{{ {key} }}}}", str(value))
            except Exception as e:
                self.logger.error(f"Computed property {key} failed: {e}")

        # Replace event handlers
        for event, handler in self.event_handlers.items():
            pattern = f"@{event}"
            processed = processed.replace(pattern, f"data-handler='{event}'")

        return processed

    def update_props(self, new_props: ComponentProps) -> None:
        """Update component props (React prop updates)."""
        old_props = self.props
        self.props = new_props

        # Trigger update if props changed
        if old_props.attributes != new_props.attributes:
            self.render()


class MeshViewerComponent(UIComponent):
    """3D Mesh viewer component (React/Vue style)."""

    def __init__(self, props: Optional[ComponentProps] = None):
        super().__init__("mesh-viewer", props)
        self.mesh_data = None
        self.viewer_settings = {
            "show_wireframe": False,
            "show_normals": False,
            "background_color": "#f0f0f0",
            "camera_position": [0, 0, 1]
        }

    def get_template(self) -> str:
        """Get mesh viewer template."""
        return '''
        <div class="mesh-viewer-container">
            <div class="viewer-toolbar">
                <button @click="toggleWireframe" class="tool-btn" title="Toggle Wireframe">
                    <span class="icon">🔗</span>
                    <span class="label">Wireframe</span>
                </button>
                <button @click="toggleNormals" class="tool-btn" title="Toggle Normals">
                    <span class="icon">📐</span>
                    <span class="label">Normals</span>
                </button>
                <button @click="resetCamera" class="tool-btn" title="Reset Camera">
                    <span class="icon">🔄</span>
                    <span class="label">Reset</span>
                </button>
            </div>
            <div class="mesh-viewer-canvas" id="viewer-canvas">
                <canvas width="800" height="600" style="border: 1px solid #ccc;">
                    {{ mesh_info }}
                </canvas>
            </div>
            <div class="viewer-info">
                <div class="info-item">
                    <span class="label">Vertices:</span>
                    <span class="value">{{ vertex_count }}</span>
                </div>
                <div class="info-item">
                    <span class="label">Faces:</span>
                    <span class="value">{{ face_count }}</span>
                </div>
                <div class="info-item">
                    <span class="label">Status:</span>
                    <span class="value">{{ loading_status }}</span>
                </div>
            </div>
        </div>
        '''

    def set_mesh_data(self, mesh_data: Dict[str, Any]) -> None:
        """Set mesh data (React/Vue data update)."""
        self.mesh_data = mesh_data
        self.set_state({
            "vertex_count": mesh_data.get("vertices", 0),
            "face_count": mesh_data.get("faces", 0),
            "mesh_info": f"Mesh loaded: {mesh_data.get('vertices', 0)} vertices",
            "loading_status": "Loaded"
        })

    def toggle_wireframe(self) -> None:
        """Toggle wireframe display."""
        self.viewer_settings["show_wireframe"] = not self.viewer_settings["show_wireframe"]
        self.set_state({"wireframe_enabled": self.viewer_settings["show_wireframe"]})

    def toggle_normals(self) -> None:
        """Toggle normals display."""
        self.viewer_settings["show_normals"] = not self.viewer_settings["show_normals"]
        self.set_state({"normals_enabled": self.viewer_settings["show_normals"]})

    def reset_camera(self) -> None:
        """Reset camera position."""
        self.viewer_settings["camera_position"] = [0, 0, 1]
        self.set_state({"camera_reset": True})


class MaterialManagerComponent(UIComponent):
    """Material management component (Vue-style with slots)."""

    def __init__(self, props: Optional[ComponentProps] = None):
        super().__init__("material-manager", props)
        self.materials = []
        self.selected_material = None

    def get_template(self) -> str:
        """Get material manager template."""
        return '''
        <div class="material-manager">
            <div class="manager-header">
                <h3>Material Library</h3>
                <button @click="addMaterial" class="add-btn">+ Add Material</button>
            </div>
            <div class="material-list">
                <div v-for="material in materials" :key="material.id"
                     class="material-item" :class="{selected: material.id === selectedId}"
                     @click="selectMaterial(material)">
                    <div class="material-preview" :style="{backgroundColor: material.color}"></div>
                    <div class="material-info">
                        <div class="material-name">{{ material.name }}</div>
                        <div class="material-type">{{ material.type }}</div>
                    </div>
                    <div class="material-actions">
                        <button @click.stop="editMaterial(material)" class="edit-btn">✏️</button>
                        <button @click.stop="deleteMaterial(material)" class="delete-btn">🗑️</button>
                    </div>
                </div>
            </div>
            <div class="material-details" v-if="selectedMaterial">
                <slot name="material-details" :material="selectedMaterial">
                    <div class="default-details">
                        <h4>{{ selectedMaterial.name }}</h4>
                        <p>Type: {{ selectedMaterial.type }}</p>
                        <p>Color: {{ selectedMaterial.color }}</p>
                        <p>Density: {{ selectedMaterial.density }} g/cm³</p>
                    </div>
                </slot>
            </div>
        </div>
        '''

    def add_material(self, material: Dict[str, Any]) -> None:
        """Add material to library."""
        self.materials.append(material)
        self.set_state({
            "materials": self.materials,
            "material_count": len(self.materials)
        })

    def select_material(self, material: Dict[str, Any]) -> None:
        """Select material."""
        self.selected_material = material
        self.set_state({
            "selected_material": material,
            "selected_id": material["id"]
        })

    def delete_material(self, material: Dict[str, Any]) -> None:
        """Delete material."""
        self.materials = [m for m in self.materials if m["id"] != material["id"]]
        if self.selected_material and self.selected_material["id"] == material["id"]:
            self.selected_material = None

        self.set_state({
            "materials": self.materials,
            "material_count": len(self.materials),
            "selected_material": self.selected_material
        })


class ProjectDashboardComponent(UIComponent):
    """Project dashboard component (React-style with hooks)."""

    def __init__(self, props: Optional[ComponentProps] = None):
        super().__init__("project-dashboard", props)
        self.projects = []
        self.stats = {
            "total_projects": 0,
            "completed_projects": 0,
            "failed_projects": 0,
            "total_print_time": 0.0
        }

        # React-style hooks simulation
        self._effects: List[Callable] = []
        self._cleanup_functions: List[Callable] = []

    def use_effect(self, effect: Callable, dependencies: List[Any]) -> None:
        """React useEffect equivalent."""
        self._effects.append((effect, dependencies))

    def use_state(self, initial_value: T) -> Tuple[T, Callable[[T], None]]:
        """React useState equivalent."""
        state_key = f"state_{len(self.state.data)}"

        if state_key not in self.state.data:
            self.state.data[state_key] = initial_value

        def set_state(new_value: T):
            self.set_state({state_key: new_value})

        return self.state.data[state_key], set_state

    def component_did_mount(self) -> None:
        """Component did mount (React equivalent)."""
        # Execute effects
        for effect, dependencies in self._effects:
            try:
                cleanup = effect()
                if cleanup:
                    self._cleanup_functions.append(cleanup)
            except Exception as e:
                self.logger.error(f"Effect execution failed: {e}")

    def component_will_unmount(self) -> None:
        """Component will unmount (React equivalent)."""
        # Execute cleanup functions
        for cleanup in self._cleanup_functions:
            try:
                cleanup()
            except Exception as e:
                self.logger.error(f"Cleanup failed: {e}")

    def get_template(self) -> str:
        """Get dashboard template."""
        return '''
        <div class="project-dashboard">
            <div class="dashboard-header">
                <h2>Project Dashboard</h2>
                <div class="dashboard-actions">
                    <button @click="refreshData" class="refresh-btn">🔄 Refresh</button>
                    <button @click="createProject" class="create-btn">+ New Project</button>
                </div>
            </div>

            <div class="dashboard-stats">
                <div class="stat-card">
                    <div class="stat-value">{{ totalProjects }}</div>
                    <div class="stat-label">Total Projects</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ completedProjects }}</div>
                    <div class="stat-label">Completed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ failedProjects }}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ totalPrintTime }}h</div>
                    <div class="stat-label">Print Time</div>
                </div>
            </div>

            <div class="dashboard-content">
                <div class="project-list">
                    <div class="list-header">
                        <h3>Recent Projects</h3>
                        <div class="list-filters">
                            <select v-model="filterStatus" @change="applyFilter">
                                <option value="all">All Projects</option>
                                <option value="completed">Completed</option>
                                <option value="in_progress">In Progress</option>
                                <option value="failed">Failed</option>
                            </select>
                        </div>
                    </div>
                    <div class="project-items">
                        <div v-for="project in filteredProjects" :key="project.id"
                             class="project-item" :class="project.status">
                            <div class="project-icon">
                                <span class="icon">{{ project.icon }}</span>
                            </div>
                            <div class="project-info">
                                <div class="project-name">{{ project.name }}</div>
                                <div class="project-status">{{ project.status }}</div>
                                <div class="project-date">{{ project.lastModified }}</div>
                            </div>
                            <div class="project-actions">
                                <button @click="openProject(project)" class="open-btn">Open</button>
                                <button @click="duplicateProject(project)" class="duplicate-btn">Copy</button>
                                <button @click="deleteProject(project)" class="delete-btn">Delete</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''

    def refresh_data(self) -> None:
        """Refresh dashboard data."""
        # Simulate API call
        mock_projects = [
            {"id": 1, "name": "Sample Project 1", "status": "completed", "icon": "📦", "lastModified": "2024-01-15"},
            {"id": 2, "name": "Current Project", "status": "in_progress", "icon": "🔧", "lastModified": "2024-01-20"},
            {"id": 3, "name": "Failed Project", "status": "failed", "icon": "❌", "lastModified": "2024-01-10"}
        ]

        self.set_state({
            "projects": mock_projects,
            "total_projects": len(mock_projects),
            "completed_projects": len([p for p in mock_projects if p["status"] == "completed"]),
            "failed_projects": len([p for p in mock_projects if p["status"] == "failed"])
        })

    def apply_filter(self) -> None:
        """Apply filter to projects."""
        filter_status = self.state.data.get("filter_status", "all")
        all_projects = self.state.data.get("projects", [])

        if filter_status == "all":
            filtered = all_projects
        else:
            filtered = [p for p in all_projects if p["status"] == filter_status]

        self.set_state({"filtered_projects": filtered})


class ModernUIFramework:
    """Modern UI framework with React/Vue patterns."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.components: Dict[str, Type[UIComponent]] = {}
        self.instances: Dict[str, UIComponent] = {}
        self.global_state: Dict[str, Any] = {}
        self.themes: Dict[str, Dict[str, str]] = {}
        self.routes: Dict[str, Type[UIComponent]] = {}

    def register_component(self, name: str, component_class: Type[UIComponent]) -> None:
        """Register component (React/Vue component registration)."""
        self.components[name] = component_class
        self.logger.info(f"Registered component: {name}")

    def create_component(self, name: str, props: Optional[ComponentProps] = None) -> Optional[UIComponent]:
        """Create component instance (React JSX equivalent)."""
        if name not in self.components:
            self.logger.error(f"Component {name} not registered")
            return None

        component_class = self.components[name]
        instance = component_class(props)
        instance_id = f"{name}_{int(time.time() * 1000)}"

        self.instances[instance_id] = instance
        self.logger.debug(f"Created component instance: {instance_id}")
        return instance

    def render_component(self, component: UIComponent, target_element: Any) -> bool:
        """Render component to DOM (React render equivalent)."""
        try:
            # Generate HTML
            html_content = component.render()

            # Update DOM element
            if hasattr(target_element, 'innerHTML'):
                target_element.innerHTML = html_content

            # Setup event handlers
            self._setup_event_handlers(component, target_element)

            # Mount children
            self._mount_children(component, target_element)

            return True

        except Exception as e:
            self.logger.error(f"Component render failed: {e}")
            return False

    def _setup_event_handlers(self, component: UIComponent, element: Any) -> None:
        """Setup event handlers for component."""
        for event_name, handler in component.event_handlers.items():
            # Find elements with data-handler attribute
            handler_elements = element.querySelectorAll(f"[data-handler='{event_name}']")

            for elem in handler_elements:
                if hasattr(elem, 'addEventListener'):
                    elem.addEventListener('click', lambda e, h=handler: h(e))

    def _mount_children(self, component: UIComponent, parent_element: Any) -> None:
        """Mount child components."""
        for child in component.children:
            # Find placeholder for child
            child_selector = f"[data-component='{child.name}']"
            child_element = parent_element.querySelector(child_selector)

            if child_element:
                self.render_component(child, child_element)

    def setup_routing(self, routes: Dict[str, Type[UIComponent]]) -> None:
        """Setup routing (React Router/Vue Router equivalent)."""
        self.routes = routes

        # Simple hash-based routing
        def handle_route_change():
            current_hash = window.location.hash.substring(1) or 'home'

            if current_hash in self.routes:
                component_class = self.routes[current_hash]
                component = self.create_component(current_hash, ComponentProps())

                if component:
                    # Find main content area
                    main_content = document.querySelector('.main-content')
                    if main_content:
                        self.render_component(component, main_content)

        # Listen for hash changes
        if hasattr(window, 'addEventListener'):
            window.addEventListener('hashchange', handle_route_change)
            handle_route_change()  # Initial route

    def setup_theme_system(self, themes: Dict[str, Dict[str, str]]) -> None:
        """Setup theme system (React/Vue theme management)."""
        self.themes = themes

        def apply_theme(theme_name: str):
            if theme_name in self.themes:
                theme_vars = self.themes[theme_name]

                # Apply CSS variables
                root = document.documentElement
                for var_name, var_value in theme_vars.items():
                    root.style.setProperty(f'--{var_name}', var_value)

        # Theme toggle functionality
        self.apply_theme = apply_theme

    def setup_state_management(self) -> None:
        """Setup global state management (Redux/Vuex equivalent)."""
        # Simple state management - in real implementation would use more sophisticated system
        def dispatch(action: Dict[str, Any]) -> None:
            action_type = action.get("type")
            payload = action.get("payload", {})

            if action_type == "UPDATE_GLOBAL_STATE":
                self.global_state.update(payload)
                # Notify all components of state change
                self._notify_components()

        def get_state() -> Dict[str, Any]:
            return self.global_state.copy()

        self.dispatch = dispatch
        self.get_state = get_state

    def _notify_components(self) -> None:
        """Notify components of state changes."""
        for instance in self.instances.values():
            # Trigger update lifecycle
            instance._trigger_lifecycle("before_update")
            instance.render()
            instance._trigger_lifecycle("updated")


class ResponsiveLayoutComponent(UIComponent):
    """Responsive layout component (React/Vue responsive design)."""

    def __init__(self, props: Optional[ComponentProps] = None):
        super().__init__("responsive-layout", props)
        self.current_breakpoint = "desktop"
        self.responsive_rules = {
            "mobile": {"max_width": 768},
            "tablet": {"max_width": 1024},
            "desktop": {"min_width": 1025}
        }

    @property
    def is_mobile(self) -> bool:
        """Check if mobile breakpoint."""
        return self.current_breakpoint == "mobile"

    @property
    def is_tablet(self) -> bool:
        """Check if tablet breakpoint."""
        return self.current_breakpoint == "tablet"

    @property
    def is_desktop(self) -> bool:
        """Check if desktop breakpoint."""
        return self.current_breakpoint == "desktop"

    def get_template(self) -> str:
        """Get responsive layout template."""
        return '''
        <div class="responsive-layout" :class="currentBreakpoint">
            <header class="layout-header">
                <div class="header-content">
                    <div class="logo">
                        <span class="logo-icon">🖨️</span>
                        <span class="logo-text">3D Print CAD</span>
                    </div>
                    <nav class="main-nav" :class="{mobile: isMobile}">
                        <a href="#dashboard" class="nav-link">Dashboard</a>
                        <a href="#projects" class="nav-link">Projects</a>
                        <a href="#materials" class="nav-link">Materials</a>
                        <a href="#settings" class="nav-link">Settings</a>
                    </nav>
                    <div class="header-actions">
                        <button class="theme-toggle" @click="toggleTheme">🌙</button>
                        <button class="mobile-menu-toggle" @click="toggleMobileMenu" v-if="isMobile">☰</button>
                    </div>
                </div>
            </header>

            <aside class="layout-sidebar" :class="{collapsed: sidebarCollapsed, mobile: isMobile}">
                <div class="sidebar-content">
                    <div class="sidebar-section">
                        <h3>Tools</h3>
                        <ul class="tool-list">
                            <li class="tool-item" :class="{active: activeTool === 'mesh'}">
                                <button @click="setActiveTool('mesh')">Mesh Editor</button>
                            </li>
                            <li class="tool-item" :class="{active: activeTool === 'slice'}">
                                <button @click="setActiveTool('slice')">Slicer</button>
                            </li>
                            <li class="tool-item" :class="{active: activeTool === 'preview'}">
                                <button @click="setActiveTool('preview')">Preview</button>
                            </li>
                        </ul>
                    </div>
                </div>
            </aside>

            <main class="layout-main">
                <div class="main-content">
                    <slot name="main-content">
                        <div class="welcome-message">
                            <h1>Welcome to 3D Print CAD Assistant</h1>
                            <p>Select a tool from the sidebar to get started.</p>
                        </div>
                    </slot>
                </div>
            </main>

            <footer class="layout-footer">
                <div class="footer-content">
                    <span>© 2024 3D Print CAD Assistant</span>
                    <span>Version 2.0.0</span>
                </div>
            </footer>
        </div>
        '''

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        current_theme = self.state.data.get("theme", "light")
        new_theme = "dark" if current_theme == "light" else "light"
        self.set_state({"theme": new_theme})

    def toggle_mobile_menu(self) -> None:
        """Toggle mobile menu."""
        current_state = self.state.data.get("mobile_menu_open", False)
        self.set_state({"mobile_menu_open": not current_state})

    def set_active_tool(self, tool: str) -> None:
        """Set active tool."""
        self.set_state({"active_tool": tool})


class AnimationSystem:
    """Animation system with React/Vue-style transitions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.animations: Dict[str, Dict[str, Any]] = {}
        self.transition_classes = {
            "fade": {"enter": "fade-enter", "leave": "fade-leave"},
            "slide": {"enter": "slide-enter", "leave": "slide-leave"},
            "scale": {"enter": "scale-enter", "leave": "scale-leave"}
        }

    def animate_component(self, component: UIComponent, animation_type: str,
                         duration: float = 0.3) -> None:
        """Animate component with specified animation."""
        if animation_type not in self.transition_classes:
            self.logger.warning(f"Unknown animation type: {animation_type}")
            return

        transition_class = self.transition_classes[animation_type]

        # Apply enter animation
        if hasattr(component.dom_element, 'classList'):
            component.dom_element.classList.add(transition_class["enter"])

            # Remove class after animation
            def remove_class():
                if hasattr(component.dom_element, 'classList'):
                    component.dom_element.classList.remove(transition_class["enter"])

            # Use timer for animation duration
            import threading
            timer = threading.Timer(duration, remove_class)
            timer.daemon = True
            timer.start()

    def create_keyframe_animation(self, name: str, keyframes: Dict[str, Dict[str, str]]) -> str:
        """Create CSS keyframe animation."""
        css_keyframes = f"@keyframes {name} {{\n"

        for percentage, properties in keyframes.items():
            css_keyframes += f"  {percentage}% {{\n"
            for prop, value in properties.items():
                css_keyframes += f"    {prop}: {value};\n"
            css_keyframes += "  }\n"

        css_keyframes += "}\n"

        # Inject CSS
        style_element = document.createElement('style')
        style_element.textContent = css_keyframes
        document.head.appendChild(style_element)

        return name


# Factory functions for React/Vue-style component creation
def create_ui_framework() -> ModernUIFramework:
    """Create modern UI framework."""
    return ModernUIFramework()


def create_mesh_viewer(props: Optional[ComponentProps] = None) -> MeshViewerComponent:
    """Create mesh viewer component."""
    return MeshViewerComponent(props)


def create_material_manager(props: Optional[ComponentProps] = None) -> MaterialManagerComponent:
    """Create material manager component."""
    return MaterialManagerComponent(props)


def create_project_dashboard(props: Optional[ComponentProps] = None) -> ProjectDashboardComponent:
    """Create project dashboard component."""
    return ProjectDashboardComponent(props)


def create_responsive_layout(props: Optional[ComponentProps] = None) -> ResponsiveLayoutComponent:
    """Create responsive layout component."""
    return ResponsiveLayoutComponent(props)


def create_animation_system() -> AnimationSystem:
    """Create animation system."""
    return AnimationSystem()
