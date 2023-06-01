import neovim
import json
import os

@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim
        option_names = ("DocCommentsEditWindowHeight", "DocCommentsEditWindowWidth",
                        "DocCommentsHighlightGroup", "DocCommentsPath",
                        "DocCommentsPreviewWidth")
        attr_names = ("edit_win_height", "edit_win_width", "highlight_group",
                      "comments_file_head", "tooltip_width")
        # Below two lines are to stop language server from thinking these
        # attributes were never assigned
        self.edit_win_height = self.edit_win_width = self.tooltip_width = 0
        self.highlight_group = self.comments_file_head = ""
        defaults = (10, 55, "Underlined", None, 50)
        for option_name, attr_name, default in zip(option_names, attr_names, defaults):
            try:
                setattr(self, attr_name, self.nvim.api.get_var(option_name))
            except neovim.pynvim.api.common.NvimError:
                setattr(self, attr_name, default)
        self.ns = self.nvim.api.create_namespace("DocComments") 
        self.set_comments_path()
        self.load_comments()
        # buffer is made unmodifiable in DocComments.vim if a comment file
        # exists because modifying text before extmarks are placed results in
        # incorrect placement. Now that extmarks ARE placed, we can allow modifications.
        self.nvim.command("set modifiable")
        # we set the below to "visual" for MakeCommentVisual, "normal" for
        # MakeCommentNormal. I'd prefer to pass this as an argument to
        # MakeCommentFunc instead of have a class attribute, but passing args
        # when using operatorfunc is not as straightforward as one would think
        self.came_from_mode = None
        # These also have to be global because you can't really pass arguments
        # to autocmd functions
        self.floating_win_handle = None
        self.close_floating_win_au_id = None

    @neovim.command("SetCommentsPath")
    def set_comments_path(self):
        buffer_name = self.nvim.api.buf_get_name(0)
        self.buffer_name = buffer_name
        buffer_head, buffer_tail = os.path.split(self.buffer_name)
        self.comments_filename = f".{buffer_tail}_comments"
        if not self.comments_file_head:
            self.comments_file = os.path.join(buffer_head, self.comments_filename)
        else:
            subdir_name = buffer_head.replace("/", "-")
            self.comments_file = os.path.join(self.comments_file_head, subdir_name, self.comments_filename)
            try:
                os.mkdir(os.path.split(self.comments_file)[0])
            except FileExistsError:
                pass
            except FileNotFoundError:
                self.nvim.api.err_write("Couldn't find directory specified in g:DocCommentsPath\n")

    @neovim.command("LoadComments")
    def load_comments(self):
        buffer_name = self.nvim.api.buf_get_name(0)
        if not os.path.isfile(buffer_name):
            return
        self.set_comments_path()
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

    @neovim.command("MakeCommentNormal", range=True)
    def make_comment_normal(self, _):  # accept range but ignore it to avoid errors
        self.came_from_mode = "normal"
        self.nvim.command("set opfunc=MakeCommentFunc")
        self.nvim.command("call feedkeys('g@')")

    @neovim.command("MakeCommentVisual", range=True)
    def make_comment_visual(self, _):  # accept range but ignore it to avoid errors
        self.came_from_mode = "visual"
        self.nvim.command("call MakeCommentFunc()")

    @neovim.function("MakeCommentFunc", range=True)
    def make_comment_func(self, *_):
        self.set_comments_path()
        start_mark = "<" if self.came_from_mode == "visual" else "["
        end_mark = ">" if self.came_from_mode == "visual" else "]"
        start_row, start_col = self.nvim.api.buf_get_mark(0, start_mark)
        if start_row == 0 and start_col == 0:
            self.nvim.command(f'echo "No text selected"')
            return
        start_row -= 1
        end_row, end_col = self.nvim.api.buf_get_mark(0, end_mark)
        # the end col is 2147483647 if the user came from visual line mode.
        # This may also may happen from normal mode if motion goes to end of
        # line, I'm not sure. This check shouldn't cause problems either way.
        if end_col == 2147483647:
            line = self.nvim.api.buf_get_lines(0, start_row, end_row, True)[0]
            end_col = len(line)-1
        end_row -= 1
        end_col += 1
        options = {
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
        mark_id = self.nvim.api.buf_set_extmark(0, self.ns, start_row, start_col, options)
        
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
        self.set_comments_path()
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

    @neovim.command("EditComment")
    def get_comment_win(self):
        self.get_comment(tooltip=False)

    @neovim.command("GetComment")
    def get_comment_tooltip(self):
        self.get_comment(tooltip=True)

    def _get_nearest_comment_id_and_text(self):
        self.set_comments_path()
        self.update_mark_locations()
        mark = self._get_mark_before_cursor()
        if not mark:
            return None, None
        if mark[2] >= mark[3]["end_col"]:  # all text inside mark was deleted
            self.nvim.api.buf_del_extmark(0, self.ns, mark[0])
            return self._get_nearest_comment_id_and_text()
        comments = self._return_comments_dict_from_file()
        comment_text = comments[str(mark[0])]["text"]
        return mark[0], comment_text

    @neovim.command("EchoComment")
    def echo_comment(self):
        _, comment_text = self._get_nearest_comment_id_and_text()
        if not comment_text:
            return
        escaped_comment_text = comment_text.replace('"', '\\"')
        self.nvim.command(f'echo "{escaped_comment_text}"')

    @neovim.function("GetCommentFunction")
    def get_comment(self, tooltip):
        comment_id, comment_text = self._get_nearest_comment_id_and_text()
        if not comment_id:
            return

        def calc_tooltip_size_from_text(text):
            text_len = len(text)
            if text_len < self.edit_win_width:
                return text_len, 1
            height = int(text_len / self.edit_win_width) + 1
            return self.edit_win_width, height

        win_width = self.nvim.api.win_get_width(0)
        win_height = self.nvim.api.call_function("winheight", [0])
        if tooltip:
            w, h = calc_tooltip_size_from_text(comment_text)
        else:
            w, h = self.edit_win_width, self.edit_win_height
        window_config = {
                "relative": "cursor" if tooltip else "win",
                "row": 1 if tooltip else int((win_height/2) - (self.edit_win_height/2)),
                "col": 1 if tooltip else int((win_width/2) - (self.edit_win_width/2)),
                "width": w,
                "height": h,
                "border": "none" if tooltip else "single",
                "focusable": not tooltip,
                "style": "minimal",
                }
        main_win = self.nvim.api.get_current_win()
        comment_buf = self.nvim.api.create_buf(False, True)
        self.floating_win_handle = self.nvim.api.open_win(comment_buf, True, window_config)
        self.nvim.api.put([comment_text], "", False, False)
        if tooltip:
            self.nvim.api.set_current_win(main_win)
            self.close_floating_win_au_id = self.nvim.api.create_autocmd(
                ["CursorMoved", "CmdlineEnter"], {"callback": "g:CloseTooltip"}
            )
        else:
            self.nvim.command(f"autocmd BufLeave <buffer> exec \"UpdateCommentText {comment_buf.handle} {comment_id}\"")

    @neovim.function("CloseTooltip")
    def close_tooltip(self, *_):
        # Even though this au immediately deletes itself, it still somehow can
        # run twice if cursor is moved and command line is entered at the same
        # time (?), for example when opening a floaterm window. This triggers
        # an error because it tries to close a window that has already closed.
        try:
            self.nvim.api.win_close(self.floating_win_handle, True)
        except neovim.pynvim.api.common.NvimError:
            pass
        finally:
            self.nvim.api.del_autocmd(self.close_floating_win_au_id)

    @neovim.command("UpdateCommentText", nargs=1)
    def update_comment_text(self, args):
        bufnum_str, mark_id = args[0].split(" ")
        lines = self.nvim.api.buf_get_lines(int(bufnum_str), 0, -1, False)
        joined_lines = "\n".join(lines)
        comments = self._return_comments_dict_from_file()
        comments[mark_id]["text"] = joined_lines
        with open(self.comments_file, "w") as f:
            f.write(json.dumps(comments))

    @neovim.command("UpdateMarkLocations")
    def update_mark_locations(self):
        self.set_comments_path()
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

