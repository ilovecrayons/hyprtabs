#pragma once

#include "window.h"
#include <gtk/gtk.h>
#include <gtk-layer-shell.h>
#include <vector>
#include <thread>
#include <atomic>

class UIManager {
public:
    UIManager();
    ~UIManager();
    
    void run();
    void show();
    void hide();
    void close();
    
private:
    // GTK widgets
    GtkWidget* window_;
    GtkWidget* main_box_;
    GtkWidget* title_label_;
    GtkWidget* list_box_;
    GtkWidget* instructions_;
    
    // Window management
    std::vector<Window> windows_;
    int current_index_;
    
    // State management
    std::atomic<bool> running_;
    std::atomic<bool> alt_pressed_;
    std::thread fifo_thread_;
    
    // Setup methods
    void setupUI();
    void setupKeybindings();
    void applyCss();
    void loadWindows();
    std::vector<Window> sortWindows(const std::vector<Window>& windows);
    
    // Window row creation
    GtkWidget* createWindowRow(const Window& window);
    
    // Navigation methods
    void updateSelection();
    void cycleNext();
    void cyclePrev();
    void activateCurrentWindow();
    
    // Event handlers
    static gboolean onKeyPress(GtkWidget* widget, GdkEventKey* event, gpointer user_data);
    static gboolean onKeyRelease(GtkWidget* widget, GdkEventKey* event, gpointer user_data);
    static void onRowActivated(GtkListBox* listbox, GtkListBoxRow* row, gpointer user_data);
    static void onRowSelected(GtkListBox* listbox, GtkListBoxRow* row, gpointer user_data);
    static gboolean onWindowDeleteEvent(GtkWidget* widget, GdkEvent* event, gpointer user_data);
    static void onWindowDestroy(GtkWidget* widget, gpointer user_data);
    
    // FIFO handling
    void startFifoListener();
    void handleFifoCommand(const std::string& command);
    static gboolean fifoCommandCallback(gpointer user_data);
    
    // Helper methods
    bool handleKeyPress(GdkEventKey* event);
    bool handleKeyRelease(GdkEventKey* event);
};
