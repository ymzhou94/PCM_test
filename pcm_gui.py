from __future__ import annotations

import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, Y, Tk, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Button, Frame, Label, Treeview

from pcm_experiments import Experiment, discover_experiments


@dataclass
class RunnerState:
    process: subprocess.Popen[str] | None = None


class UnifiedPCMGui:
    def __init__(self, root: Tk, repo_root: Path) -> None:
        self.root = root
        self.repo_root = repo_root
        self.state = RunnerState()
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.experiments = discover_experiments(repo_root)
        self.tree_items: dict[str, Experiment] = {}

        self.root.title("PCM Unified Experiment Launcher")
        self._build_layout()
        self._populate_tree()
        self._poll_output()

    def _build_layout(self) -> None:
        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=12, pady=12)

        left_frame = Frame(main_frame)
        left_frame.pack(side=LEFT, fill=Y)

        right_frame = Frame(main_frame)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left_frame, text="Experiments").pack(anchor="w")

        self.tree = Treeview(left_frame, show="tree")
        self.tree.pack(fill=Y, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        details_frame = Frame(right_frame)
        details_frame.pack(fill=BOTH)

        Label(details_frame, text="Selected script:").pack(anchor="w")
        self.selected_label = Label(details_frame, text="None")
        self.selected_label.pack(anchor="w")

        button_frame = Frame(details_frame)
        button_frame.pack(fill=BOTH, pady=8)

        self.run_button = Button(button_frame, text="Run", command=self._run_selected)
        self.run_button.pack(side=LEFT, padx=4)

        self.stop_button = Button(button_frame, text="Stop", command=self._stop_running)
        self.stop_button.pack(side=LEFT, padx=4)
        self.stop_button.state(["disabled"])

        self.clear_button = Button(button_frame, text="Clear Log", command=self._clear_log)
        self.clear_button.pack(side=LEFT, padx=4)

        self.output = ScrolledText(right_frame, height=20)
        self.output.pack(fill=BOTH, expand=True)

    def _populate_tree(self) -> None:
        categories: dict[str, list[Experiment]] = {}
        for experiment in self.experiments:
            categories.setdefault(experiment.category, []).append(experiment)

        for category, experiments in categories.items():
            category_id = self.tree.insert("", END, text=category, open=True)
            for experiment in experiments:
                item_id = self.tree.insert(category_id, END, text=experiment.display_name)
                self.tree_items[item_id] = experiment

    def _on_tree_select(self, _event: object) -> None:
        selected = self._selected_experiment()
        if selected is None:
            self.selected_label.config(text="None")
            return
        self.selected_label.config(text=str(selected.path.relative_to(self.repo_root)))

    def _selected_experiment(self) -> Experiment | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.tree_items.get(selection[0])

    def _run_selected(self) -> None:
        experiment = self._selected_experiment()
        if experiment is None:
            messagebox.showwarning("Select experiment", "Please select a script to run.")
            return
        if self.state.process is not None:
            messagebox.showinfo("Running", "An experiment is already running.")
            return

        command = [sys.executable, str(experiment.path)]
        self._append_output(f"Launching: {' '.join(command)}\n")

        self.state.process = subprocess.Popen(
            command,
            cwd=self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.run_button.state(["disabled"])
        self.stop_button.state(["!disabled"])

        thread = threading.Thread(target=self._read_output, daemon=True)
        thread.start()

    def _read_output(self) -> None:
        process = self.state.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            self.output_queue.put(line)
        process.wait()
        self.output_queue.put("\n[Process finished]\n")
        self.root.after(0, self._process_finished)

    def _process_finished(self) -> None:
        self.state.process = None
        self.run_button.state(["!disabled"])
        self.stop_button.state(["disabled"])

    def _stop_running(self) -> None:
        process = self.state.process
        if process is None:
            return
        process.terminate()
        self._append_output("\n[Terminating process]\n")

    def _clear_log(self) -> None:
        self.output.delete("1.0", END)

    def _append_output(self, text: str) -> None:
        self.output.insert(END, text)
        self.output.see(END)

    def _poll_output(self) -> None:
        while not self.output_queue.empty():
            line = self.output_queue.get()
            self._append_output(line)
        self.root.after(200, self._poll_output)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    root = Tk()
    UnifiedPCMGui(root, repo_root)
    root.mainloop()


if __name__ == "__main__":
    main()
