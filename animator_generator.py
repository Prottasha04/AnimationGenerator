import os
import tkinter as tk


def animator_generator(file_path):
    ref_var = []       
    primitive_var = [] 
    objects = {}
    code_lines = []
    line_items = []

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return code_lines, line_items, ref_var, primitive_var, objects

    with open(file_path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            code_index = len(code_lines)
            code_lines.append(raw_line.rstrip('\n'))
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue

            
            if line.startswith('variable:'):
                clean_var = line.replace('variable:', '').strip()

               
                if '->' in clean_var:
                    parts = clean_var.split('->')
                    if len(parts) == 2:
                        v_name = parts[0].strip()
                        t_id = parts[1].strip()
                        ref_var.append((v_name, t_id))
                        line_items.append((code_index, 'ref_var', (v_name, t_id)))

              
                elif '=' in clean_var:
                    parts = clean_var.split('=', 1)
                    var_label = parts[0].strip()
                    var_val = parts[1].strip()
                    primitive_var.append((var_label, var_val))
                    line_items.append((code_index, 'primitive_var', (var_label, var_val)))

           
            elif line.startswith('object:'):
                parts = line.replace('object:', '').strip().split('|')
                if len(parts) >= 2:
                    obj_id = parts[0].strip()
                    obj_type = parts[1].strip()
                    fields_raw = parts[2].strip() if len(parts) > 2 else ""

                    fields = {}
                    if fields_raw:
                        for field_str in fields_raw.split(','):
                            field_str = field_str.strip()
                            if '=' in field_str:
                                k, v = field_str.split('=', 1)
                                k = k.strip().split()[-1]
                                fields[k] = v.strip().strip('"\'')
                            elif ':' in field_str:
                                k, v = field_str.split(':', 1)
                                fields[k.strip()] = v.strip().strip('"\'')

                    objects[obj_id] = (obj_type, fields)
                    line_items.append((code_index, 'object', obj_id))

    return code_lines, line_items, ref_var, primitive_var, objects


class Visualizer:
    def __init__(self, root, file_path):
        self.root = root
        root.title('Java O-O Visualizer')
        #changed
        self.code, self.line_items, self.ref_var, self.primitive_var, self.objects = animator_generator(file_path)

        self.string_objs = {k: v for k, v in self.objects.items() if v[0] == 'String'}
        self.regular_objs = {k: v for k, v in self.objects.items() if v[0] != 'String'}

        num_regular = max(len(self.regular_objs), 1)
        num_primitives = len(self.primitive_var)

        self.start_x = 3.8 if num_primitives == 0 else 6.0
        self.canvas_width = max(12, self.start_x + (num_regular * 5.2))
        self.canvas_height = 8.5
        self.scale = min(75, int(1050 / self.canvas_width)) if self.canvas_width > 14 else 75

        canvas_px_w = int(self.canvas_width * self.scale)
        canvas_px_h = int(self.canvas_height * self.scale)

        root.geometry(f'{canvas_px_w + 460}x{max(790, canvas_px_h + 110)}')
        root.minsize(1200, 790)

        self.compute_layout()
        self.steps = self.build_steps()

        self.step = 0
        self.animating = False
        self.playing = False
        self.timer = None
        self.drawn_vars = set()
        self.drawn_objs = set()

        left = tk.Frame(root, padx=18, pady=18)
        left.pack(side='left', fill='both', expand=True)

        right = tk.Frame(root, padx=10, pady=18)
        right.pack(side='right', fill='y')

        tk.Label(left, text='Java Code', font=('Arial', 19, 'bold')).pack(anchor='w')

        self.code_box = tk.Text(
            left,
            height=14,
            width=43,
            font=('Courier', 13),
            wrap='none',
            padx=10,
            pady=15,
            bg='#f5f5f5',
            relief='flat'
        )
        self.code_box.pack(fill='x', pady=(12, 15))

        for line in self.code:
            self.code_box.insert('end', line + '\n')

        self.code_box.tag_configure('active', background='#ffe49a')
        self.code_box.configure(state='disabled')

        self.status = tk.Label(
            left,
            text='',
            font=('Arial', 12),
            anchor='w',
            justify='left',
            wraplength=420
        )
        self.status.pack(fill='x', pady=8)

        controls = tk.Frame(left)
        controls.pack(anchor='w', pady=10)

        self.next_button = tk.Button(controls, text='Next Step', width=12, command=self.next_step)
        self.next_button.pack(side='left', padx=(0, 8))

        self.play_button = tk.Button(controls, text='Auto Play', width=12, command=self.toggle_play)
        self.play_button.pack(side='left', padx=(0, 8))

        tk.Button(controls, text='Reset', width=9, command=self.reset).pack(side='left')

        tk.Label(right, text='Memory Diagram', font=('Arial', 19, 'bold')).pack()

        self.canvas = tk.Canvas(
            right,
            width=canvas_px_w,
            height=canvas_px_h,
            bg='white',
            highlightthickness=1,
            highlightbackground='#ddd'
        )
        self.canvas.pack(pady=12)

        self.reset()

    def to_px(self, x, y):
        return x * self.scale, (self.canvas_height - y) * self.scale

    def compute_layout(self):
        self.prim_coords = {}
        self.var_box_coords = {}
        self.obj_coords = {}
        self.field_box_coords = {}

        
        for idx, (var_label, var_val) in enumerate(self.primitive_var):
            vx = 0.8 + (idx * 2.0)
            vy = 7.4
            self.prim_coords[(var_label, var_val)] = self.to_px(vx + 0.5, vy)

       
        spacing = 5.2
        for idx, (obj_id, (obj_type, fields)) in enumerate(self.regular_objs.items()):
            cx = self.start_x + idx * spacing
            cy = 3.2
            radius = 1.85
            self.obj_coords[obj_id] = (cx, cy, radius)

            field_items = list(fields.items())
            for i, (f_name, f_val) in enumerate(field_items):
                fx = cx - 0.7 + (i % 2) * 1.4
                fy = cy - 0.5 if len(field_items) <= 2 else (cy - 0.2 if i < 2 else cy - 0.9)
                val_str = str(f_val)
                box_w = max(0.9, len(val_str) * 0.13)
                if f_val in self.string_objs:
                    self.field_box_coords[(obj_id, f_name)] = (fx - box_w / 2.0, fy, box_w)

       
        parent_string_counts = {}
        unref_count = 0
        for str_id, (obj_type, fields) in self.string_objs.items():
            parent_id = None
            for p_id, (p_type, p_fields) in self.regular_objs.items():
                if str_id in p_fields.values():
                    parent_id = p_id
                    break

            if parent_id in self.obj_coords:
                parent_cx, parent_cy, _ = self.obj_coords[parent_id]
                count = parent_string_counts.get(parent_id, 0)
                parent_string_counts[parent_id] = count + 1
                cx = parent_cx + 2 + (count * 2.2)
                cy = parent_cy + 2.8
            else:
                cx = 1.8 + (unref_count * 2.3)
                cy = 5.2
                unref_count += 1

            radius = 1.0
            self.obj_coords[str_id] = (cx, cy, radius)

       
        target_ref_counts = {}
        for var_name, target_id in self.ref_var:
            if target_id in self.obj_coords:
                tcx, tcy, trad = self.obj_coords[target_id]
                count = target_ref_counts.get(target_id, 0)
                target_ref_counts[target_id] = count + 1
                vx = tcx - 1.4 + (count * 1.3)
                vy = tcy + trad + 0.45
                self.var_box_coords[var_name] = (vx + 0.5, vy, tcx - 0.4, tcy + trad - 0.1)

    def build_steps(self):
        steps = []
        for code_index, kind, payload in self.line_items:
            if kind == 'primitive_var':
                var_label, var_val = payload
                steps.append({
                    "code_index": code_index,
                    "label": f'Create primitive variable {var_label} with value {var_val}',
                    "action": "primitive_var",
                    "payload": payload
                })
            elif kind == 'ref_var':
                var_name, target_id = payload
                steps.append({
                    "code_index": code_index,
                    "label": f'Create variable {var_name}',
                    "action": "ref_var",
                    "payload": payload
                })
            elif kind == 'object':
                obj_id = payload
                obj_type, _ = self.objects[obj_id]
                steps.append({
                    "code_index": code_index,
                    "label": f'Create {obj_type} ({obj_id})',
                    "action": "object",
                    "payload": obj_id
                })
        return steps

    def highlight(self, index):
        self.code_box.configure(state='normal')
        self.code_box.tag_remove('active', '1.0', 'end')
        self.code_box.tag_add('active', f'{index+1}.0', f'{index+1}.end')
        self.code_box.configure(state='disabled')

    def draw_variable(self, name, x, y, value=None):
        self.canvas.create_text(x, y - 28, text=name, font=('Arial', 12, 'bold'))
        self.canvas.create_rectangle(x - 34, y - 17, x + 34, y + 17, width=2)
        if value is not None:
            self.canvas.create_text(x, y, text=str(value), font=('Arial', 12))

    def draw_regular_object(self, obj_id):
        obj_type, fields = self.regular_objs[obj_id]
        cx, cy, radius = self.obj_coords[obj_id]
        px, py = self.to_px(cx, cy)
        r_px = radius * self.scale

        self.canvas.create_oval(px - r_px, py - r_px, px + r_px, py + r_px, width=2.5)
        self.canvas.create_text(px, py - r_px + (0.45 * self.scale), text=obj_type, font=('Arial', 16, 'bold'))

        field_items = list(fields.items())
        for i, (f_name, f_val) in enumerate(field_items):
            fx = cx - 0.7 + (i % 2) * 1.4
            fy = cy - 0.5 if len(field_items) <= 2 else (cy - 0.2 if i < 2 else cy - 0.9)
            fpx, fpy = self.to_px(fx, fy)

            self.canvas.create_text(fpx, fpy - (0.4 * self.scale), text=f_name, font=('Arial', 11))

            val_str = str(f_val)
            box_w_px = max(0.9, len(val_str) * 0.13) * self.scale
            box_h_px = 0.5 * self.scale
            self.canvas.create_rectangle(
                fpx - box_w_px / 2.0, fpy - box_h_px / 2.0,
                fpx + box_w_px / 2.0, fpy + box_h_px / 2.0,
                width=1.5
            )

            if f_val not in self.string_objs:
                self.canvas.create_text(fpx, fpy, text=val_str, font=('Arial', 10))

    def draw_string_object(self, str_id):
        _, fields = self.string_objs[str_id]
        cx, cy, radius = self.obj_coords[str_id]
        px, py = self.to_px(cx, cy)
        r_px = radius * self.scale

        self.canvas.create_oval(px - r_px, py - r_px, px + r_px, py + r_px, width=2)
        self.canvas.create_text(px, py - (0.35 * self.scale), text='String', font=('Arial', 13))

        val = fields.get('value', fields.get('val', ''))
        self.canvas.create_text(px, py + (0.15 * self.scale), text=f'"{val}"', font=('Arial', 11))

    def animate_reverse_arrow(self, start, end, done, bend=-25, tag=None):
        sx, sy = start
        ex, ey = end

        mx = (sx + ex) / 2
        my = (sy + ey) / 2 + bend

        points = []
        for i in range(41):
            t = i / 40
            x = (1-t)**2 * sx + 2*(1-t)*t * mx + t*t * ex
            y = (1-t)**2 * sy + 2*(1-t)*t * my + t*t * ey
            points.append((x, y))

        line = self.canvas.create_line(
            ex, ey, ex, ey,
            fill='#2475b8',
            width=3,
            arrow=tk.LAST,
            arrowshape=(12, 14, 5),
            tags=tag
        )

        self.animating = True

        def frame(i):
            section = points[40-i:]
            coords = [coord for point in section for coord in point]

            if len(coords) < 4:
                coords = [ex, ey, ex, ey]

            self.canvas.coords(line, *coords)

            if i < 40:
                self.timer = self.root.after(16, lambda: frame(i + 1))
            else:
                self.animating = False
                done()

        frame(0)

    def run_arrow_chain(self, arrows, done):
        if not arrows:
            done()
            return
        start, end, bend = arrows[0]
        self.animate_reverse_arrow(
            start, end,
            lambda: self.run_arrow_chain(arrows[1:], done),
            bend=bend
        )

    def next_step(self):
        if self.animating or self.step >= len(self.steps):
            return

        current = self.step
        self.step += 1

        step_info = self.steps[current]
        code_index = step_info["code_index"]
        action = step_info["action"]
        label = step_info["label"]
        payload = step_info["payload"]

        self.highlight(code_index)
        self.status.config(
            text=f'Step {self.step}/{len(self.steps)}: {self.code[code_index].strip()}\n{label}'
        )

        if action == "primitive_var":
            var_label, var_val = payload
            px, py = self.prim_coords[(var_label, var_val)]
            self.draw_variable(var_label, px, py, value=var_val)
            self.after_step()

        elif action == "ref_var":
            var_name, target_id = payload
            self.drawn_vars.add(var_name)
            if var_name in self.var_box_coords:
                sx, sy, tx, ty = self.var_box_coords[var_name]
                start_px = self.to_px(sx, sy)
                self.draw_variable(var_name, start_px[0], start_px[1])
                if target_id in self.drawn_objs:
                    end_px = self.to_px(tx, ty)
                    self.animate_reverse_arrow(start_px, end_px, self.after_step)
                else:
                    self.after_step()
            else:
                self.after_step()

        elif action == "object":
            obj_id = payload
            self.drawn_objs.add(obj_id)
            arrows_to_draw = []

            if obj_id in self.regular_objs:
                self.draw_regular_object(obj_id)
                _, fields = self.regular_objs[obj_id]
                for f_name, f_val in fields.items():
                    if f_val in self.drawn_objs and (obj_id, f_name) in self.field_box_coords:
                        box_left_x, box_center_y, box_w = self.field_box_coords[(obj_id, f_name)]
                        scx, scy, srad = self.obj_coords[f_val]
                        start_px = self.to_px(box_left_x + (box_w / 2.0), box_center_y)
                        end_px = self.to_px(scx, scy - srad)
                        arrows_to_draw.append((start_px, end_px, 25))

            elif obj_id in self.string_objs:
                self.draw_string_object(obj_id)
                for (p_id, f_name), (box_left_x, box_center_y, box_w) in self.field_box_coords.items():
                    if p_id in self.drawn_objs and self.objects[p_id][1][f_name] == obj_id:
                        scx, scy, srad = self.obj_coords[obj_id]
                        start_px = self.to_px(box_left_x + (box_w / 2.0), box_center_y)
                        end_px = self.to_px(scx, scy - srad)
                        arrows_to_draw.append((start_px, end_px, 25))

            for v_name, t_id in self.ref_var:
                if t_id == obj_id and v_name in self.drawn_vars and v_name in self.var_box_coords:
                    sx, sy, tx, ty = self.var_box_coords[v_name]
                    arrows_to_draw.append((self.to_px(sx, sy), self.to_px(tx, ty), -25))

            self.run_arrow_chain(arrows_to_draw, self.after_step)

    def after_step(self):
        if self.step == len(self.steps):
            self.playing = False
            self.play_button.config(text='Auto Play')
            self.status.config(text='Finished! All animation steps have been simulated.')
        elif self.playing:
            self.timer = self.root.after(700, self.next_step)

    def toggle_play(self):
        self.playing = not self.playing
        self.play_button.config(text='Pause' if self.playing else 'Auto Play')

        if self.playing and not self.animating:
            if self.timer is not None:
                self.root.after_cancel(self.timer)
                self.timer = None
            self.next_step()

    def reset(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

        self.animating = False
        self.playing = False
        self.step = 0
        self.drawn_vars.clear()
        self.drawn_objs.clear()

        self.play_button.config(text='Auto Play')
        self.canvas.delete('all')

        self.code_box.configure(state='normal')
        self.code_box.tag_remove('active', '1.0', 'end')
        self.code_box.configure(state='disabled')

        self.status.config(text='Click Next Step to begin.')


if __name__ == '__main__':
    file_path = input("Input .txt file: ").strip().strip('"\'')
    root = tk.Tk()
    Visualizer(root, file_path)
    root.mainloop()