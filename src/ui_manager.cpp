#include "ui_manager.h"
#include "hyprland_manager.h"
#include "singleton_manager.h"
#include "constants.h"
#include <gdk/gdk.h>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <unistd.h>

UIManager::UIManager() 
    : window_(nullptr), main_box_(nullptr), title_label_(nullptr), 
      list_box_(nullptr), instructions_(nullptr), current_index_(0),
      running_(true), alt_pressed_(false) {
    
    setupUI();
}

UIManager::~UIManager() {
    running_ = false;
    if (fifo_thread_.joinable()) {
        fifo_thread_.join();
    }
    // Ensure singleton lock is released even if close() wasn't called
    SingletonManager::releaseLock();
}

void UIManager::setupUI() {
    // Create main window
    window_ = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window_), "HyprTabs");
    
    // Initialize layer shell
    gtk_layer_init_for_window(GTK_WINDOW(window_));
    
    // Set layer shell properties for instant display
    gtk_layer_set_layer(GTK_WINDOW(window_), GTK_LAYER_SHELL_LAYER_OVERLAY);
    gtk_layer_set_namespace(GTK_WINDOW(window_), "hyprtabs");
    
    // Set anchors to center the window
    gtk_layer_set_anchor(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_TOP, FALSE);
    gtk_layer_set_anchor(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_BOTTOM, FALSE);
    gtk_layer_set_anchor(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_LEFT, FALSE);
    gtk_layer_set_anchor(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_RIGHT, FALSE);
    
    // Enable exclusive keyboard interaction for instant focus
    gtk_layer_set_keyboard_mode(GTK_WINDOW(window_), GTK_LAYER_SHELL_KEYBOARD_MODE_EXCLUSIVE);
    
    // Set margins to center the window
    gtk_layer_set_margin(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_TOP, 0);
    gtk_layer_set_margin(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_BOTTOM, 0);
    gtk_layer_set_margin(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_LEFT, 0);
    gtk_layer_set_margin(GTK_WINDOW(window_), GTK_LAYER_SHELL_EDGE_RIGHT, 0);
    
    // Remove regular window properties that don't apply to layer shell
    gtk_window_set_decorated(GTK_WINDOW(window_), FALSE);
    gtk_window_set_resizable(GTK_WINDOW(window_), FALSE);
    
    // Set fixed size to avoid resizing
    gtk_widget_set_size_request(window_, 600, 400);
    gtk_window_set_default_size(GTK_WINDOW(window_), 600, 400);
    
    // Set geometry hints to prevent resizing
    GdkGeometry geometry;
    geometry.min_width = 600;
    geometry.min_height = 400;
    geometry.max_width = 600;
    geometry.max_height = 400;
    gtk_window_set_geometry_hints(GTK_WINDOW(window_), nullptr, &geometry,
                                  static_cast<GdkWindowHints>(GDK_HINT_MIN_SIZE | GDK_HINT_MAX_SIZE));
    
    // Optimize for speed
    gtk_widget_set_can_focus(window_, TRUE);
    gtk_widget_set_can_default(window_, TRUE);
    gtk_widget_add_events(window_, GDK_KEY_PRESS_MASK | GDK_KEY_RELEASE_MASK);
    
    // Main container with minimal spacing
    main_box_ = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_top(main_box_, 15);
    gtk_widget_set_margin_bottom(main_box_, 15);
    gtk_widget_set_margin_start(main_box_, 15);
    gtk_widget_set_margin_end(main_box_, 15);
    gtk_container_add(GTK_CONTAINER(window_), main_box_);
    
    // Title label
    title_label_ = gtk_label_new(nullptr);
    gtk_label_set_markup(GTK_LABEL(title_label_), "<b>Alt+Tab Window Switcher</b>");
    gtk_box_pack_start(GTK_BOX(main_box_), title_label_, FALSE, FALSE, 0);
    
    // Window list - optimize for performance
    list_box_ = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(list_box_), GTK_SELECTION_SINGLE);
    gtk_list_box_set_activate_on_single_click(GTK_LIST_BOX(list_box_), TRUE);
    gtk_widget_set_can_focus(list_box_, FALSE);
    
    // Connect mouse click events
    g_signal_connect(list_box_, "row-activated", G_CALLBACK(onRowActivated), this);
    g_signal_connect(list_box_, "row-selected", G_CALLBACK(onRowSelected), this);
    
    gtk_box_pack_start(GTK_BOX(main_box_), list_box_, TRUE, TRUE, 0);
    
    // Instructions
    instructions_ = gtk_label_new(nullptr);
    gtk_label_set_markup(GTK_LABEL(instructions_),
                        "<small>Hold Alt + Tab to cycle • Release Alt to switch • Esc to cancel</small>");
    gtk_box_pack_start(GTK_BOX(main_box_), instructions_, FALSE, FALSE, 0);
    
    // Apply CSS immediately
    applyCss();
    
    // Setup keybindings
    setupKeybindings();
}

void UIManager::applyCss() {
    const char* css = R"(
        window {
            background-color: rgba(0, 0, 0, 0.9);
            border-radius: 10px;
            border: 2px solid #555;
        }
        
        * {
            transition: none;
            animation: none;
        }
        
        .window-item {
            padding: 10px;
            margin: 2px;
            border-radius: 5px;
            background-color: rgba(255, 255, 255, 0.1);
            min-height: 60px;
        }
        
        .window-item:selected {
            background-color: rgba(100, 150, 255, 0.8);
        }
        
        .window-active {
            background-color: rgba(0, 100, 150, 0.3);
        }
        
        .window-active:selected {
            background-color: rgba(0, 100, 150, 0.8);
            border-left: 6px solid #00ff66;
            border-right: 6px solid #00ff66;
        }

        .window-active:hover {
            background-color: rgba(0, 100, 255, 0.8);
        }
        
        .window-hidden {
            background-color: rgba(100, 0, 0, 0.3);
        }
        
        .window-hidden:selected {
            background-color: rgba(100, 0, 0, 0.8);
            border-left: 6px solid #ff3333;
            border-right: 6px solid #ff3333;
        }

        .window-hidden:hover {
            background-color: rgba(200, 0, 0, 0.8);
        }
        
        .minimized {
            color: #888;
        }
        
        .workspace-number {
            opacity: 0.5;
            font-weight: bold;
            font-size: 14px;
            color: #ffffff;
            min-width: 25px;
        }
    )";
    
    GtkCssProvider* provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, css, -1, nullptr);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION
    );
    g_object_unref(provider);
}

void UIManager::setupKeybindings() {
    g_signal_connect(window_, "key-press-event", G_CALLBACK(onKeyPress), this);
    g_signal_connect(window_, "key-release-event", G_CALLBACK(onKeyRelease), this);
    g_signal_connect(window_, "delete-event", G_CALLBACK(onWindowDeleteEvent), this);
    g_signal_connect(window_, "destroy", G_CALLBACK(onWindowDestroy), this);
}

void UIManager::loadWindows() {
    windows_ = HyprlandManager::getAllWindows();
    windows_ = sortWindows(windows_);
    
    // Clear existing items efficiently
    GList* children = gtk_container_get_children(GTK_CONTAINER(list_box_));
    for (GList* iter = children; iter != nullptr; iter = g_list_next(iter)) {
        gtk_widget_destroy(GTK_WIDGET(iter->data));
    }
    g_list_free(children);
    
    // Add all rows
    for (const auto& window : windows_) {
        GtkWidget* row = createWindowRow(window);
        gtk_list_box_insert(GTK_LIST_BOX(list_box_), row, -1);
    }
    
    // Select first item immediately
    if (!windows_.empty()) {
        current_index_ = 0;
        GtkListBoxRow* row = gtk_list_box_get_row_at_index(GTK_LIST_BOX(list_box_), 0);
        if (row) {
            gtk_list_box_select_row(GTK_LIST_BOX(list_box_), row);
        }
        
        // Set initial title
        const auto& current_window = windows_[0];
        std::string status = current_window.isMinimized() ? "Hidden" : "WS " + std::to_string(current_window.getWorkspace());
        std::string title_text = "<b>1/" + std::to_string(windows_.size()) + "</b> - " + 
                                current_window.getClassName() + " (" + status + ")";
        gtk_label_set_markup(GTK_LABEL(title_label_), title_text.c_str());
    }
    
    // Assume Alt is pressed for faster startup
    alt_pressed_ = true;
    
    // Show everything at once
    gtk_widget_show_all(window_);
    
    // Start FIFO listener
    startFifoListener();
}

std::vector<Window> UIManager::sortWindows(const std::vector<Window>& windows) {
    if (windows.empty()) {
        return windows;
    }
    
    // Get the currently active window
    auto active_window = HyprlandManager::getActiveWindow();
    std::string active_address = active_window ? active_window->getAddress() : "";
    
    // Separate the currently active window from the rest
    std::vector<Window> result;
    std::vector<Window> other_windows;
    
    for (const auto& window : windows) {
        if (window.getAddress() == active_address) {
            result.push_back(window);
        } else {
            other_windows.push_back(window);
        }
    }
    
    // Sort other windows by workspace, then by visibility status
    std::sort(other_windows.begin(), other_windows.end(), [](const Window& a, const Window& b) {
        // Primary sort: workspace number (minimized windows go last)
        int workspace_a = a.isMinimized() ? std::numeric_limits<int>::max() : a.getWorkspace();
        int workspace_b = b.isMinimized() ? std::numeric_limits<int>::max() : b.getWorkspace();
        
        if (workspace_a != workspace_b) {
            return workspace_a < workspace_b;
        }
        
        // Secondary sort: active windows before hidden ones
        return !a.isMinimized() && b.isMinimized();
    });
    
    // Combine: current window first, then sorted other windows
    result.insert(result.end(), other_windows.begin(), other_windows.end());
    
    return result;
}

GtkWidget* UIManager::createWindowRow(const Window& window) {
    GtkWidget* row = gtk_list_box_row_new();
    GtkStyleContext* context = gtk_widget_get_style_context(row);
    gtk_style_context_add_class(context, "window-item");
    
    // Add state class
    const char* state_class = window.isMinimized() ? "window-hidden" : "window-active";
    gtk_style_context_add_class(context, state_class);
    
    GtkWidget* box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    
    // Icon - use fixed size for consistency
    GtkWidget* status_label = gtk_label_new(window.getIcon().c_str());
    gtk_widget_set_size_request(status_label, 30, -1);
    gtk_box_pack_start(GTK_BOX(box), status_label, FALSE, FALSE, 0);
    
    // Window info - single vertical box
    GtkWidget* info_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    
    // Title with fixed width
    GtkWidget* title_label = gtk_label_new(nullptr);
    gtk_widget_set_halign(title_label, GTK_ALIGN_START);
    std::string title_markup = "<b>" + window.getClassName() + "</b>";
    gtk_label_set_markup(GTK_LABEL(title_label), title_markup.c_str());
    gtk_label_set_ellipsize(GTK_LABEL(title_label), PANGO_ELLIPSIZE_END);
    gtk_label_set_max_width_chars(GTK_LABEL(title_label), 40);
    gtk_widget_set_size_request(title_label, 300, -1);
    gtk_box_pack_start(GTK_BOX(info_box), title_label, FALSE, FALSE, 0);
    
    // Subtitle with fixed width
    GtkWidget* subtitle_label = gtk_label_new(nullptr);
    gtk_widget_set_halign(subtitle_label, GTK_ALIGN_START);
    gtk_label_set_ellipsize(GTK_LABEL(subtitle_label), PANGO_ELLIPSIZE_END);
    gtk_label_set_max_width_chars(GTK_LABEL(subtitle_label), 50);
    gtk_label_set_width_chars(GTK_LABEL(subtitle_label), 50);
    gtk_widget_set_size_request(subtitle_label, 400, -1);
    
    if (window.isMinimized()) {
        GtkStyleContext* subtitle_context = gtk_widget_get_style_context(subtitle_label);
        gtk_style_context_add_class(subtitle_context, "minimized");
        std::string subtitle_markup = "<i>" + window.getTitle() + " (Hidden)</i>";
        gtk_label_set_markup(GTK_LABEL(subtitle_label), subtitle_markup.c_str());
    } else {
        gtk_label_set_text(GTK_LABEL(subtitle_label), window.getTitle().c_str());
    }
    
    gtk_box_pack_start(GTK_BOX(info_box), subtitle_label, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), info_box, TRUE, TRUE, 0);
    
    // Workspace number or spacer
    if (!window.isMinimized()) {
        GtkWidget* workspace_label = gtk_label_new(std::to_string(window.getWorkspace()).c_str());
        GtkStyleContext* ws_context = gtk_widget_get_style_context(workspace_label);
        gtk_style_context_add_class(ws_context, "workspace-number");
        gtk_widget_set_halign(workspace_label, GTK_ALIGN_CENTER);
        gtk_widget_set_valign(workspace_label, GTK_ALIGN_CENTER);
        gtk_widget_set_size_request(workspace_label, 30, -1);
        gtk_box_pack_end(GTK_BOX(box), workspace_label, FALSE, FALSE, 0);
    } else {
        // Add empty space for consistent sizing
        GtkWidget* spacer_label = gtk_label_new("");
        gtk_widget_set_size_request(spacer_label, 30, -1);
        gtk_box_pack_end(GTK_BOX(box), spacer_label, FALSE, FALSE, 0);
    }
    
    gtk_container_add(GTK_CONTAINER(row), box);
    return row;
}

void UIManager::updateSelection() {
    std::cout << "updateSelection() called, windows size: " << windows_.size() << ", current_index: " << current_index_ << std::endl;
    if (windows_.empty()) {
        return;
    }
    
    // Ensure index is valid
    current_index_ = current_index_ % windows_.size();
    std::cout << "Validated current_index: " << current_index_ << std::endl;
    
    // Select the row immediately without animations
    GtkListBoxRow* row = gtk_list_box_get_row_at_index(GTK_LIST_BOX(list_box_), current_index_);
    if (row) {
        std::cout << "Found row at index " << current_index_ << ", selecting it" << std::endl;
        gtk_list_box_select_row(GTK_LIST_BOX(list_box_), row);
        gtk_widget_grab_focus(GTK_WIDGET(row));
    } else {
        std::cout << "No row found at index " << current_index_ << std::endl;
    }
    
    // Update title with current window info
    if (current_index_ < windows_.size()) {
        const auto& current_window = windows_[current_index_];
        std::string status = current_window.isMinimized() ? "Hidden" : "WS " + std::to_string(current_window.getWorkspace());
        std::string title_text = "<b>" + std::to_string(current_index_ + 1) + "/" + std::to_string(windows_.size()) + 
                                "</b> - " + current_window.getClassName() + " (" + status + ")";
        gtk_label_set_markup(GTK_LABEL(title_label_), title_text.c_str());
    }
}

void UIManager::cycleNext() {
    std::cout << "cycleNext() called, windows size: " << windows_.size() << ", current_index: " << current_index_ << std::endl;
    if (!windows_.empty()) {
        current_index_ = (current_index_ + 1) % windows_.size();
        std::cout << "New current_index: " << current_index_ << std::endl;
        updateSelection();
    }
}

void UIManager::cyclePrev() {
    if (!windows_.empty()) {
        current_index_ = (current_index_ - 1 + windows_.size()) % windows_.size();
        updateSelection();
    }
}

void UIManager::activateCurrentWindow() {
    if (windows_.empty() || current_index_ >= windows_.size()) {
        return;
    }
    
    const auto& window = windows_[current_index_];
    
    hide();
    
    // Process any pending GTK events
    while (gtk_events_pending()) {
        gtk_main_iteration_do(FALSE);
    }
    
    // Focus the window
    HyprlandManager::focusWindow(window);
    
    // Allow time for window manager to process before terminating
    g_timeout_add(100, [](gpointer user_data) -> gboolean {
        static_cast<UIManager*>(user_data)->close();
        return FALSE;
    }, this);
}

void UIManager::startFifoListener() {
    fifo_thread_ = std::thread([this]() {
        try {
            while (running_) {
                std::ifstream fifo(Constants::FIFO_FILE);
                if (!fifo.is_open()) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                    continue;
                }
                
                std::string line;
                while (running_ && std::getline(fifo, line)) {
                    if (!line.empty()) {
                        // Schedule the command to be handled in the main thread
                        g_idle_add_full(G_PRIORITY_DEFAULT, 
                                       [](gpointer user_data) -> gboolean {
                                           auto* data = static_cast<std::pair<UIManager*, std::string>*>(user_data);
                                           data->first->handleFifoCommand(data->second);
                                           delete data;
                                           return FALSE;
                                       }, 
                                       new std::pair<UIManager*, std::string>(this, line), 
                                       nullptr);
                    }
                }
            }
        } catch (const std::exception&) {
            // Ignore errors
        }
    });
}

void UIManager::handleFifoCommand(const std::string& command) {
    if (command == "next") {
        cycleNext();
    } else if (command == "prev") {
        cyclePrev();
    } else if (command == "activate") {
        activateCurrentWindow();
    } else if (command == "close") {
        close();
    }
}

gboolean UIManager::onKeyPress(GtkWidget* widget, GdkEventKey* event, gpointer user_data) {
    auto* ui = static_cast<UIManager*>(user_data);
    return ui->handleKeyPress(event) ? TRUE : FALSE;
}

gboolean UIManager::onKeyRelease(GtkWidget* widget, GdkEventKey* event, gpointer user_data) {
    auto* ui = static_cast<UIManager*>(user_data);
    return ui->handleKeyRelease(event) ? TRUE : FALSE;
}

void UIManager::onRowActivated(GtkListBox* listbox, GtkListBoxRow* row, gpointer user_data) {
    auto* ui = static_cast<UIManager*>(user_data);
    if (!row) return;
    
    int clicked_index = gtk_list_box_row_get_index(row);
    if (clicked_index >= 0 && clicked_index < ui->windows_.size()) {
        ui->current_index_ = clicked_index;
        ui->updateSelection();
        ui->activateCurrentWindow();
    }
}

void UIManager::onRowSelected(GtkListBox* listbox, GtkListBoxRow* row, gpointer user_data) {
    auto* ui = static_cast<UIManager*>(user_data);
    if (!row) return;
    
    int selected_index = gtk_list_box_row_get_index(row);
    if (selected_index >= 0 && selected_index < ui->windows_.size()) {
        ui->current_index_ = selected_index;
        ui->updateSelection();
    }
}

bool UIManager::handleKeyPress(GdkEventKey* event) {
    guint keyval = event->keyval;
    GdkModifierType state = static_cast<GdkModifierType>(event->state);
    
    std::cout << "Key pressed: " << keyval << " (GDK_KEY_Tab=" << GDK_KEY_Tab << "), state: " << state << std::endl;
    
    // Track Alt key state
    if (keyval == GDK_KEY_Alt_L || keyval == GDK_KEY_Alt_R || (state & GDK_MOD1_MASK)) {
        alt_pressed_ = true;
        std::cout << "Alt pressed detected" << std::endl;
    }
    
    // Check for Alt+Tab or Tab while Alt is held
    if (keyval == GDK_KEY_Tab) {
        std::cout << "Tab key detected, current_index before: " << current_index_ << std::endl;
        if (state & GDK_SHIFT_MASK) {
            std::cout << "Calling cyclePrev()" << std::endl;
            cyclePrev();
        } else {
            std::cout << "Calling cycleNext()" << std::endl;
            cycleNext();
        }
        std::cout << "Tab key handled, current_index after: " << current_index_ << std::endl;
        return true;
    }
    
    // Enter or Space to activate
    if (keyval == GDK_KEY_Return || keyval == GDK_KEY_space || keyval == GDK_KEY_KP_Enter) {
        activateCurrentWindow();
        return true;
    }
    
    // Escape to cancel
    if (keyval == GDK_KEY_Escape) {
        close();
        return true;
    }
    
    // Arrow keys for navigation
    if (keyval == GDK_KEY_Down || keyval == GDK_KEY_j) {
        cycleNext();
        return true;
    }
    if (keyval == GDK_KEY_Up || keyval == GDK_KEY_k) {
        cyclePrev();
        return true;
    }
    
    return false;
}

bool UIManager::handleKeyRelease(GdkEventKey* event) {
    guint keyval = event->keyval;
    GdkModifierType state = static_cast<GdkModifierType>(event->state);
    
    // Check for Alt key release
    if (keyval == GDK_KEY_Alt_L || keyval == GDK_KEY_Alt_R) {
        alt_pressed_ = false;
        activateCurrentWindow();
        return true;
    }
    
    // Also check if Alt modifier is no longer active (fallback)
    if (alt_pressed_ && !(state & GDK_MOD1_MASK)) {
        alt_pressed_ = false;
        activateCurrentWindow();
        return true;
    }
    
    return false;
}

void UIManager::run() {
    loadWindows();
    gtk_main();
}

void UIManager::show() {
    gtk_widget_show_all(window_);
}

void UIManager::hide() {
    gtk_widget_hide(window_);
}

void UIManager::close() {
    running_ = false;
    
    // Process any remaining events before quitting
    while (gtk_events_pending()) {
        gtk_main_iteration_do(FALSE);
    }
    
    // Release singleton lock before destroying window
    SingletonManager::releaseLock();
    
    gtk_widget_destroy(window_);
    gtk_main_quit();
}

gboolean UIManager::onWindowDeleteEvent(GtkWidget* widget, GdkEvent* event, gpointer user_data) {
    auto* ui = static_cast<UIManager*>(user_data);
    ui->close();
    return TRUE; // Prevent default handler
}

void UIManager::onWindowDestroy(GtkWidget* widget, gpointer user_data) {
    auto* ui = static_cast<UIManager*>(user_data);
    ui->running_ = false;
    // Ensure lock is released even if close() wasn't called
    SingletonManager::releaseLock();
    gtk_main_quit();
}
