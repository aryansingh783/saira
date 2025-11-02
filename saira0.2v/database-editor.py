# qa_editor_enhanced.py
# Enhanced QA Blocks Editor with flexible answers
# Requirements: Python builtin Tkinter only
# Run: python qa_editor_enhanced.py

import os
import re
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
from datetime import datetime

QA_FILE = "qa_blocks.txt"
BACKUP_DIR = "backups"

def parse_blocks(text):
    parts = text.split('---BLOCK---')
    blocks = []
    for p in parts:
        p = p.strip()
        if not p: continue
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        b = {"id": None, "q": "", "answers": [], "tags": [], "difficulty": "Medium"}
        for ln in lines:
            if ln.lower().startswith("id:"):
                b["id"] = ln.split(":",1)[1].strip()
            elif ln.lower().startswith("q:"):
                b["q"] = ln.split(":",1)[1].strip()
            elif ln.lower().startswith("tags:"):
                b["tags"] = [t.strip() for t in ln.split(":",1)[1].split(",") if t.strip()]
            elif ln.lower().startswith("difficulty:"):
                b["difficulty"] = ln.split(":",1)[1].strip()
            elif re.match(r'^a\d+\s*:', ln, flags=re.I):
                b["answers"].append(ln.split(":",1)[1].strip())
            else:
                if not b["q"]:
                    b["q"] = ln
                else:
                    b["answers"].append(ln)
        blocks.append(b)
    return blocks

def blocks_to_text(blocks):
    out = []
    for b in blocks:
        out.append("---BLOCK---")
        if b.get("id"):
            out.append(f"ID: {b['id']}")
        out.append(f"Q: {b['q']}")
        if b.get("tags"):
            out.append(f"Tags: {', '.join(b['tags'])}")
        if b.get("difficulty"):
            out.append(f"Difficulty: {b['difficulty']}")
        for i, a in enumerate(b["answers"], start=1):
            if a:
                out.append(f"A{i}: {a}")
    return "\n".join(out)

class EditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QA Blocks Editor Pro")
        self.geometry("1200x700")
        self.blocks = []
        self.filtered_blocks = []
        self.current_index = 0
        self.unsaved_changes = False
        self.answer_widgets = []  # Dynamic answer widgets
        
        # Create backup directory
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Set style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure colors
        self.configure(bg='#f0f0f0')
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('TButton', padding=6)
        
        self.load_file()
        self.create_widgets()
        
        # Bind save shortcut
        self.bind('<Control-s>', lambda e: self.save_file())
        self.bind('<Control-f>', lambda e: self.search_entry.focus())
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_file(self):
        if not os.path.exists(QA_FILE):
            with open(QA_FILE, "w", encoding="utf-8") as f:
                f.write("")
        text = open(QA_FILE, "r", encoding="utf-8").read()
        self.blocks = parse_blocks(text)
        self.filtered_blocks = self.blocks.copy()

    def save_file(self):
        # Create backup
        if os.path.exists(QA_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"qa_blocks_{timestamp}.txt")
            with open(QA_FILE, "r", encoding="utf-8") as f:
                backup_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        
        # Save current
        text = blocks_to_text(self.blocks)
        with open(QA_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        
        self.unsaved_changes = False
        self.update_title()
        messagebox.showinfo("Saved", f"File saved successfully!\nBackup created in {BACKUP_DIR}/")

    def update_title(self):
        title = "QA Blocks Editor Pro"
        if self.unsaved_changes:
            title += " *"
        if self.blocks:
            title += f" - {len(self.blocks)} blocks"
        self.title(title)

    def create_widgets(self):
        # Main container
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel
        left = ttk.Frame(main, width=350)
        left.pack(side="left", fill="both", padx=5, pady=5)
        left.pack_propagate(False)
        
        # Search and filter frame
        search_frame = ttk.Frame(left)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(search_frame, text="🔍 Search:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        ttk.Button(search_frame, text="Clear", command=self.clear_search, width=6).pack(side="left", padx=(5, 0))
        
        # Stats frame
        stats_frame = ttk.Frame(left)
        stats_frame.pack(fill="x", pady=(0, 10))
        self.stats_label = ttk.Label(stats_frame, text="Total: 0 blocks", font=('Arial', 9))
        self.stats_label.pack(side="left")
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                   font=('Arial', 10), activestyle='none',
                                   selectbackground='#0078d4', selectforeground='white')
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        self.refresh_listbox()
        
        # Left button frame
        btn_frame = ttk.Frame(left)
        btn_frame.pack(pady=10, fill="x")
        
        ttk.Button(btn_frame, text="➕ Add", command=self.add_block).pack(side="left", padx=2, expand=True, fill="x")
        ttk.Button(btn_frame, text="🗑️ Delete", command=self.delete_block).pack(side="left", padx=2, expand=True, fill="x")
        ttk.Button(btn_frame, text="📋 Duplicate", command=self.duplicate_block).pack(side="left", padx=2, expand=True, fill="x")
        
        btn_frame2 = ttk.Frame(left)
        btn_frame2.pack(pady=(0, 10), fill="x")
        
        ttk.Button(btn_frame2, text="💾 Save", command=self.save_file).pack(side="left", padx=2, expand=True, fill="x")
        ttk.Button(btn_frame2, text="🔄 Reload", command=self.reload_file).pack(side="left", padx=2, expand=True, fill="x")
        ttk.Button(btn_frame2, text="📁 Export", command=self.export_json).pack(side="left", padx=2, expand=True, fill="x")
        
        # Right panel
        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header = ttk.Frame(right)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Edit Block", style='Title.TLabel').pack(side="left")
        self.block_counter = ttk.Label(header, text="Block 0/0", font=('Arial', 10))
        self.block_counter.pack(side="right")
        
        # Editor area with canvas for scrolling
        self.canvas = tk.Canvas(right, bg='white', highlightthickness=0)
        scrollbar_right = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar_right.set)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar_right.pack(side="right", fill="y")
        
        # Form fields (will be created dynamically)
        self.form = ttk.Frame(self.scrollable_frame)
        self.form.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Navigation bar at bottom
        nav = ttk.Frame(right)
        nav.pack(fill="x", pady=(10, 0))
        
        ttk.Button(nav, text="⬅️ Previous", command=self.prev_block).pack(side="left", padx=2)
        ttk.Button(nav, text="Next ➡️", command=self.next_block).pack(side="left", padx=2)
        ttk.Button(nav, text="✅ Update", command=self.update_block).pack(side="right", padx=2)
        ttk.Button(nav, text="➕ Add Answer", command=self.add_answer_field).pack(side="right", padx=2)
        ttk.Button(nav, text="➖ Remove Answer", command=self.remove_answer_field).pack(side="right", padx=2)
        
        if self.blocks:
            self.show_block(0)
        
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.update_title()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def mark_unsaved(self):
        self.unsaved_changes = True
        self.update_title()

    def create_editor_form(self, num_answers=5):
        """Dynamically create editor form with specified number of answer fields"""
        # Clear existing form
        for widget in self.form.winfo_children():
            widget.destroy()
        
        self.answer_widgets = []
        
        # ID
        id_frame = ttk.Frame(self.form)
        id_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(id_frame, text="ID:", font=('Arial', 10, 'bold')).pack(side="left", padx=(0, 10))
        self.id_entry = ttk.Entry(id_frame, font=('Arial', 10))
        self.id_entry.pack(side="left", fill="x", expand=True)
        self.id_entry.bind('<KeyRelease>', lambda e: self.mark_unsaved())
        
        # Difficulty
        diff_frame = ttk.Frame(id_frame)
        diff_frame.pack(side="left", padx=(10, 0))
        ttk.Label(diff_frame, text="Difficulty:").pack(side="left", padx=(0, 5))
        self.difficulty_var = tk.StringVar(value="Medium")
        difficulty_combo = ttk.Combobox(diff_frame, textvariable=self.difficulty_var, 
                                       values=["Easy", "Medium", "Hard"], width=10, state="readonly")
        difficulty_combo.pack(side="left")
        difficulty_combo.bind('<<ComboboxSelected>>', lambda e: self.mark_unsaved())
        
        # Tags
        tags_frame = ttk.Frame(self.form)
        tags_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(tags_frame, text="Tags (comma-separated):", font=('Arial', 10, 'bold')).pack(anchor="w", pady=(0, 5))
        self.tags_entry = ttk.Entry(tags_frame, font=('Arial', 10))
        self.tags_entry.pack(fill="x")
        self.tags_entry.bind('<KeyRelease>', lambda e: self.mark_unsaved())
        
        # Question
        ttk.Label(self.form, text="Question:", font=('Arial', 10, 'bold')).pack(anchor="w", pady=(10, 5))
        q_frame = ttk.Frame(self.form)
        q_frame.pack(fill="x", pady=(0, 10))
        q_scroll = ttk.Scrollbar(q_frame)
        q_scroll.pack(side="right", fill="y")
        self.q_text = tk.Text(q_frame, height=4, font=('Arial', 10), wrap="word", yscrollcommand=q_scroll.set)
        self.q_text.pack(side="left", fill="both", expand=True)
        q_scroll.config(command=self.q_text.yview)
        self.q_text.bind('<KeyRelease>', lambda e: self.mark_unsaved())
        
        # Answers section label with count
        ans_header = ttk.Frame(self.form)
        ans_header.pack(fill="x", pady=(10, 5))
        ttk.Label(ans_header, text=f"Answers ({num_answers}):", font=('Arial', 10, 'bold')).pack(side="left")
        ttk.Label(ans_header, text="Use buttons below to add/remove answers", 
                 font=('Arial', 8), foreground='gray').pack(side="left", padx=(10, 0))
        
        # Answers - dynamic creation
        for i in range(num_answers):
            ans_container = ttk.Frame(self.form)
            ans_container.pack(fill="x", pady=(5, 5))
            
            label_frame = ttk.Frame(ans_container)
            label_frame.pack(fill="x")
            ttk.Label(label_frame, text=f"Answer {i+1}:", font=('Arial', 10, 'bold')).pack(side="left")
            
            a_frame = ttk.Frame(ans_container)
            a_frame.pack(fill="x", pady=(2, 0))
            a_scroll = ttk.Scrollbar(a_frame)
            a_scroll.pack(side="right", fill="y")
            t = tk.Text(a_frame, height=3, font=('Arial', 10), wrap="word", yscrollcommand=a_scroll.set)
            t.pack(side="left", fill="both", expand=True)
            a_scroll.config(command=t.yview)
            t.bind('<KeyRelease>', lambda e: self.mark_unsaved())
            
            self.answer_widgets.append(t)
        
        # Update canvas scroll region
        self.form.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_answer_field(self):
        """Add one more answer field"""
        current_count = len(self.answer_widgets)
        
        # Save current data
        current_data = self.get_current_form_data()
        
        # Recreate form with one more answer
        self.create_editor_form(current_count + 1)
        
        # Restore data
        self.set_form_data(current_data)
        
        # Scroll to bottom to show new field
        self.canvas.yview_moveto(1.0)
        
        messagebox.showinfo("Added", f"Answer field {current_count + 1} added!")

    def remove_answer_field(self):
        """Remove last answer field"""
        current_count = len(self.answer_widgets)
        
        if current_count <= 1:
            messagebox.showwarning("Cannot Remove", "At least 1 answer field is required!")
            return
        
        # Check if last field has content
        last_answer = self.answer_widgets[-1].get("1.0", "end").strip()
        if last_answer:
            if not messagebox.askyesno("Confirm", "Last answer has content. Remove anyway?"):
                return
        
        # Save current data (excluding last answer)
        current_data = self.get_current_form_data()
        current_data['answers'] = current_data['answers'][:-1]
        
        # Recreate form with one less answer
        self.create_editor_form(current_count - 1)
        
        # Restore data
        self.set_form_data(current_data)
        
        messagebox.showinfo("Removed", f"Answer field {current_count} removed!")

    def get_current_form_data(self):
        """Get all current form data"""
        return {
            'id': self.id_entry.get().strip(),
            'q': self.q_text.get("1.0", "end").strip(),
            'tags': self.tags_entry.get().strip(),
            'difficulty': self.difficulty_var.get(),
            'answers': [t.get("1.0", "end").strip() for t in self.answer_widgets]
        }

    def set_form_data(self, data):
        """Set form data"""
        self.id_entry.delete(0, "end")
        self.id_entry.insert(0, data.get('id', ''))
        
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, data.get('tags', ''))
        
        self.difficulty_var.set(data.get('difficulty', 'Medium'))
        
        self.q_text.delete("1.0", "end")
        self.q_text.insert("1.0", data.get('q', ''))
        
        answers = data.get('answers', [])
        for i, widget in enumerate(self.answer_widgets):
            widget.delete("1.0", "end")
            if i < len(answers):
                widget.insert("1.0", answers[i])

    def refresh_listbox(self):
        self.listbox.delete(0, "end")
        for i, b in enumerate(self.filtered_blocks):
            ans_count = len([a for a in b.get('answers', []) if a])
            title = f"{b.get('id') or i+1}: {b['q'][:45]}"
            if ans_count > 0:
                title += f" ({ans_count}A)"
            if b.get('tags'):
                title += f" [{', '.join(b['tags'][:2])}]"
            self.listbox.insert("end", title)
        
        total = len(self.blocks)
        shown = len(self.filtered_blocks)
        if shown < total:
            self.stats_label.config(text=f"Showing: {shown} / {total} blocks")
        else:
            self.stats_label.config(text=f"Total: {total} blocks")

    def on_search(self, event=None):
        query = self.search_entry.get().lower()
        if not query:
            self.filtered_blocks = self.blocks.copy()
        else:
            self.filtered_blocks = [b for b in self.blocks 
                                   if query in b['q'].lower() 
                                   or any(query in a.lower() for a in b.get('answers', []))
                                   or any(query in t.lower() for t in b.get('tags', []))]
        self.refresh_listbox()
        if self.filtered_blocks:
            self.listbox.selection_set(0)
            self.show_block(0)

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.on_search()

    def on_select(self, evt):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.show_block(idx)

    def show_block(self, idx):
        if idx < 0 or idx >= len(self.filtered_blocks):
            return
            
        self.current_index = idx
        b = self.filtered_blocks[idx]
        
        # Get actual number of answers (including empty ones for proper display)
        num_answers = max(len(b.get('answers', [])), 5)  # Minimum 5 fields
        
        # Create form with correct number of answer fields
        self.create_editor_form(num_answers)
        
        # Set data
        self.id_entry.delete(0, "end")
        if b.get("id"):
            self.id_entry.insert(0, b["id"])
        
        self.tags_entry.delete(0, "end")
        if b.get("tags"):
            self.tags_entry.insert(0, ", ".join(b["tags"]))
        
        self.difficulty_var.set(b.get("difficulty", "Medium"))
        
        self.q_text.delete("1.0", "end")
        self.q_text.insert("1.0", b["q"])
        
        answers = b.get('answers', [])
        for i, widget in enumerate(self.answer_widgets):
            widget.delete("1.0", "end")
            if i < len(answers):
                widget.insert("1.0", answers[i])
        
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        
        self.block_counter.config(text=f"Block {idx+1}/{len(self.filtered_blocks)} ({num_answers} answers)")
        
        # Reset scroll to top
        self.canvas.yview_moveto(0)

    def update_block(self):
        b = self.filtered_blocks[self.current_index]
        original_idx = self.blocks.index(b)
        
        self.blocks[original_idx]["id"] = self.id_entry.get().strip()
        self.blocks[original_idx]["q"] = self.q_text.get("1.0", "end").strip()
        self.blocks[original_idx]["answers"] = [t.get("1.0", "end").strip() for t in self.answer_widgets]
        self.blocks[original_idx]["difficulty"] = self.difficulty_var.get()
        
        tags_text = self.tags_entry.get().strip()
        self.blocks[original_idx]["tags"] = [t.strip() for t in tags_text.split(",") if t.strip()]
        
        self.mark_unsaved()
        self.refresh_listbox()
        self.listbox.selection_set(self.current_index)
        messagebox.showinfo("Updated", "Block updated! Don't forget to Save (Ctrl+S)")

    def add_block(self):
        new_id = str(len(self.blocks) + 1)
        new = {"id": new_id, "q": "New question here", "answers": [""], "tags": [], "difficulty": "Medium"}
        self.blocks.append(new)
        self.mark_unsaved()
        
        # Clear search to show all
        self.search_entry.delete(0, "end")
        self.filtered_blocks = self.blocks.copy()
        self.refresh_listbox()
        
        self.show_block(len(self.filtered_blocks)-1)

    def duplicate_block(self):
        if not self.filtered_blocks:
            return
        
        b = self.filtered_blocks[self.current_index].copy()
        b["id"] = str(len(self.blocks) + 1)
        b["q"] = b["q"] + " (Copy)"
        b["answers"] = b.get("answers", []).copy()
        b["tags"] = b.get("tags", []).copy()
        
        self.blocks.append(b)
        self.mark_unsaved()
        
        self.search_entry.delete(0, "end")
        self.filtered_blocks = self.blocks.copy()
        self.refresh_listbox()
        
        self.show_block(len(self.filtered_blocks)-1)

    def delete_block(self):
        if not self.filtered_blocks:
            return
        
        if messagebox.askyesno("Delete", "Delete this block permanently?"):
            b = self.filtered_blocks[self.current_index]
            self.blocks.remove(b)
            self.filtered_blocks.remove(b)
            self.mark_unsaved()
            
            self.refresh_listbox()
            
            if self.filtered_blocks:
                new_idx = min(self.current_index, len(self.filtered_blocks)-1)
                self.show_block(new_idx)
            else:
                self.create_editor_form(5)

    def prev_block(self):
        if self.current_index > 0:
            self.show_block(self.current_index - 1)

    def next_block(self):
        if self.current_index < len(self.filtered_blocks) - 1:
            self.show_block(self.current_index + 1)

    def reload_file(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Reload", "You have unsaved changes. Reload anyway?"):
                return
        
        self.load_file()
        self.search_entry.delete(0, "end")
        self.refresh_listbox()
        self.unsaved_changes = False
        
        if self.blocks:
            self.show_block(0)
        else:
            self.create_editor_form(5)
        
        self.update_title()

    def export_json(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"qa_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.blocks, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Exported", f"Exported {len(self.blocks)} blocks to JSON!")

    def on_closing(self):
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("Quit", "Save changes before closing?")
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.save_file()
        
        self.destroy()

if __name__ == "__main__":
    app = EditorApp()
    app.mainloop()