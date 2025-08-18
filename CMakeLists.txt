cmake_minimum_required(VERSION 3.16)
project(hyprtabs)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)

# Find GTK3
pkg_check_modules(GTK3 REQUIRED gtk+-3.0)

# Find GTK Layer Shell
pkg_check_modules(LAYER_SHELL REQUIRED gtk-layer-shell-0)

# Find JSON library
find_package(nlohmann_json REQUIRED)

# Include directories
include_directories(${GTK3_INCLUDE_DIRS})
include_directories(${LAYER_SHELL_INCLUDE_DIRS})
include_directories(src)

# Link directories
link_directories(${GTK3_LIBRARY_DIRS})
link_directories(${LAYER_SHELL_LIBRARY_DIRS})

# Compiler flags
add_definitions(${GTK3_CFLAGS_OTHER})
add_definitions(${LAYER_SHELL_CFLAGS_OTHER})

# Add compiler flags for optimization
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -DNDEBUG")

# Source files
set(SOURCES
    src/main.cpp
    src/window.cpp
    src/hyprland_manager.cpp
    src/ui_manager.cpp
    src/singleton_manager.cpp
    src/constants.cpp
)

# Create executable
add_executable(hyprtabs ${SOURCES})

# Link libraries
target_link_libraries(hyprtabs 
    ${GTK3_LIBRARIES} 
    ${LAYER_SHELL_LIBRARIES}
    nlohmann_json::nlohmann_json
    pthread
)

# Install target
install(TARGETS hyprtabs DESTINATION bin)
