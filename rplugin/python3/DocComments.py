import neovim
import json
import random
import os

@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim
        self.ns = self.nvim.api.create_namespace("DocComments") 
        self.buffer_name = self.nvim.api.buf_get_name(0)
        head, tail = os.path.split(self.buffer_name)
        comments_filename = f".{tail}_comments"
        self.comments_file = os.path.join(head, comments_filename)
        option_names = ("DocCommentsPreviewHeight", "DocCommentsPreviewWidth", "DocCommentsHighlightGroup")
        attr_names = ("preview_height", "preview_width", "highlight_group")
        defaults = (10, 55, "Underlined")
        for option_name, attr_name, default in zip(option_names, attr_names, defaults):
            try:
                setattr(self, attr_name, self.nvim.api.get_var(option_name))
            except neovim.pynvim.api.common.NvimError:
                setattr(self, attr_name, default)
        self.load_comments()

    @neovim.command("UpdateFileNames")
    def update_file_names(self):
        buffer_name = self.nvim.api.buf_get_name(0)
        if not os.path.isfile(buffer_name) or buffer_name == self.buffer_name:
            return
        self.buffer_name = buffer_name
        head, tail = os.path.split(self.buffer_name)
        comments_filename = f".{tail}_comments"
        self.comments_file = os.path.join(head, comments_filename)

    @neovim.command("LoadComments")
    def load_comments(self):
        buffer_name = self.nvim.api.buf_get_name(0)
        if not os.path.isfile(buffer_name):
            return
        self.update_file_names()
        marks = self.nvim.api.buf_get_extmarks(0, self.ns, 0, -1, {"details": True})
        for mark in marks:
            self.nvim.api.buf_del_extmark(0, self.ns, mark[0])
        comments = self._return_comments_dict_from_file()
        if comments == {}:
            return
        for id_num in comments:
            contents = comments[id_num]
            options = {
                    "id": int(id_num),
                    "end_row": contents["end_row"],
                    "end_col": contents["end_col"],
                    "hl_group": self.highlight_group,
                    }
            self.nvim.api.buf_set_extmark(0, self.ns, contents["row"], contents["col"], options)

    def _return_comments_dict_from_file(self):
        if not os.path.isfile(self.comments_file):
            return {}
        with open(self.comments_file) as f:
            try:
                ret = json.load(f)
            except json.JSONDecodeError:  # probably empty, which shouldn't happen
                ret = {}
            return ret

    @neovim.command("MakeComment", range=True)
    def make_comment(self, rng):  # accept range but ignore it to avoid errors
        self.update_file_names()
        start_row, start_col = self.nvim.api.buf_get_mark(0, "<")
        start_row -= 1
        end_row, end_col = self.nvim.api.buf_get_mark(0, ">")
        if end_col == 2147483647:  # came from visual line mode
            line = self.nvim.api.buf_get_lines(0, start_row, end_row, True)[0]
            end_col = len(line)-1
        end_row -= 1
        end_col += 1
        mark_id = random.randint(0, 9223372036854775807)
        options = {
                "id": mark_id,
                "end_row": end_row,
                "end_col": end_col,
                "hl_group": self.highlight_group
                }
        # Get user input for comment
        self.nvim.api.call_function("inputsave", [])
        comment_text = self.nvim.api.call_function("input", ["Comment: "])
        self.nvim.api.call_function("inputrestore", [])
        if comment_text == "":  # user hit <esc> or entered nothing
            return
        self.nvim.api.buf_set_extmark(0, self.ns, start_row, start_col, options)
        
        # save mark to file
        comments = self._return_comments_dict_from_file()
        comments[mark_id] = {
            "text": comment_text, "row": start_row,
            "col": start_col, "end_row": end_row,
            "end_col": end_col,
            }
        with open(self.comments_file, "w") as f:
            f.write(json.dumps(comments))

    def _get_mark_before_cursor(self):
        cursor_pos = self.nvim.api.win_get_cursor(0)
        cursor_pos[0] -= 1
        try:
            mark = self.nvim.api.buf_get_extmarks(0, self.ns, cursor_pos, [cursor_pos[0], 0], {"limit":1, "details": True})[0]
        except IndexError:
            return None
        return mark

    @neovim.command("DeleteComment")
    def delete_comment(self):
        self.update_file_names()
        self.update_mark_locations()
        mark = self._get_mark_before_cursor()
        if not mark:
            return
        mark_id = mark[0]
        self.nvim.api.buf_del_extmark(0, self.ns, mark_id)
        comments = self._return_comments_dict_from_file()
        del comments[str(mark_id)]
        with open(self.comments_file, "w") as f:
            f.write(json.dumps(comments))

    @neovim.command("GetComment")
    def get_comment(self):
        self.update_file_names()
        self.update_mark_locations()
        mark = self._get_mark_before_cursor()
        if not mark:
            return
        if mark[2] >= mark[3]["end_col"]:  # all text inside mark was deleted
            self.nvim.api.buf_del_extmark(0, self.ns, mark[0])
            self.get_comment()
        else:  # got our mark!
            win_width = self.nvim.api.win_get_width(0)
            win_height = self.nvim.api.call_function("winheight", [0])
            window_config = {
                    "relative": "win",
                    "row": int((win_height/2) - (self.preview_height/2)),
                    "col": int((win_width/2) - (self.preview_width/2)),
                    "width": self.preview_width,
                    "height": self.preview_height,
                    "border": "single",
                    "style": "minimal",
                    }
            buf = self.nvim.api.create_buf(False, True)
            self.nvim.api.open_win(buf, True, window_config)
            comments = self._return_comments_dict_from_file()
            comment_text = comments[str(mark[0])]["text"]
            self.nvim.api.put([comment_text], "", False, False)
            self.nvim.api.buf_set_option(buf, "modifiable", False)

    @neovim.command("UpdateMarkLocations")
    def update_mark_locations(self):
        self.update_file_names()
        marks = self.nvim.api.buf_get_extmarks(0, self.ns, 0, -1, {"details": True})
        comments = self._return_comments_dict_from_file()
        if comments == {}:  # user never set a comment
            return
        for mark in marks:
            mark_id, row, col = mark[0], mark[1], mark[2]
            end_row, end_col = mark[3]["end_row"], mark[3]["end_col"]
            if col >= end_col:  # delete 0 width marks
                del comments[str(mark_id)]
                self.nvim.api.buf_del_extmark(0, self.ns, mark_id)
                continue
            comments[str(mark_id)]["row"] = row
            comments[str(mark_id)]["col"] = col
            comments[str(mark_id)]["end_row"] = end_row
            comments[str(mark_id)]["end_col"] = end_col
        with open(self.comments_file, "w") as f:
            f.write(json.dumps(comments))
