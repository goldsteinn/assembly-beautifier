;;; abfify.el --- (automatically) format python buffers using ABF.

;; Copyright (C) 2016 Joris Engbers

;; Author: Joris Engbers <info@jorisengbers.nl>
;; Homepage: https://github.com/JorisE/abfify
;; Version: 0.0.9
;; Package-Version: 20200406.830
;; Package-Commit: 3df4e8ce65f55fd69479b3417525ce83a2b00b45
;; Package-Requires: ()

;; This file is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published
;; by the Free Software Foundation; either version 3, or (at your
;; option) any later version.
;;
;; This file is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.
;;
;; For a full copy of the GNU General Public License
;; see <http://www.gnu.org/licenses/>.

;;; Commentary:
;;
;; Abfify uses abf to format a Python buffer. It can be called explicitly on a
;; certain buffer, but more conveniently, a minor-mode 'abf-mode' is provided
;; that turns on automatically running ABF on a buffer before saving.
;;
;; Installation:
;;
;; Add abfify.el to your load-path.
;;
;; To automatically format all Python buffers before saving, add the function
;; abf-mode to python-mode-hook:
;;
;; (add-hook 'python-mode-hook 'abf-mode)
;;
;;; Code:

(require 'cl-lib)

(defcustom abfify-executable "asm_beautifier.py"
  "Executable used to start abf."
  :type 'string
  :group 'abfify)

(defun abfify-call-bin (input-buffer output-buffer start-line end-line arg3 arg4)
  "Call process abf on INPUT-BUFFER saving the output to OUTPUT-BUFFER.

Return the exit code.  START-LINE and END-LINE specify region to
format."
  (with-current-buffer input-buffer
    (call-process-region (point-min) (point-max)
                         abfify-executable nil output-buffer
                         nil "-l" "--lines" (concat (number-to-string start-line) ","
                                                    (number-to-string end-line)) arg3 arg4)))

(defun get-buffer-string (buffer)
  "Return the contents of BUFFER."
  (with-current-buffer buffer
    (buffer-string)))

;;;###autoload
(defun abfify-region-kernel (beginning end arg3 arg4)
  "Try to abfify the current region.

If abf exits with an error, the output will be shown in a help-window."
  (interactive "r")
  (when (get-buffer "*abfify*")
    (kill-buffer "*abfify*"))
  (let* ((original-buffer (current-buffer))
         (original-point (point))  ; Because we are replacing text, save-excursion does not always work.
         (buffer-windows (get-buffer-window-list original-buffer nil t))
         (original-window-pos (mapcar 'window-start buffer-windows))
         (start-line (line-number-at-pos beginning))
         (end-line (line-number-at-pos (if (or (= (char-before end) 10)
                                               (= (char-before end) 13))
                                           (- end 1)
                                         end)))

         (tmpbuf (get-buffer-create "*abfify*"))
         (exit-code (abfify-call-bin original-buffer tmpbuf start-line end-line arg3 arg4)))
    (deactivate-mark)
    ;; There are three exit-codes defined for ABF:
    ;; 0: Exit with success (change or no change on abf >=0.11)
    ;; 1: Exit with error
    ;; 2: Exit with success and change (Backward compatibility)
    ;; anything else would be very unexpected.
    (cond ((eq exit-code 0)
           (with-current-buffer tmpbuf
             (copy-to-buffer original-buffer (point-min) (point-max))))
          ((eq exit-code 1)
           (error "Abf failed, see %s buffer for details" (buffer-name tmpbuf))))
    ;; Clean up tmpbuf
    ;;(kill-buffer tmpbuf)
    ;; restore window to similar state
    (goto-char original-point)
    (cl-mapcar 'set-window-start buffer-windows original-window-pos))) 

;;;###autoload
(defun abfify-buffer ()
  "Abfify whole buffer."
  (interactive)
  (abfify-region-kernel (point-min) (point-max) "--none" "--none"))

;;;###autoload
(defun abfify-region ()
  "Abfify whole buffer."
  (interactive)
  (message "aasdadfsdfs")
  (abfify-region-kernel (region-beginning) (region-end) "--no-indent" "--no-skip"))

;;;###autoload
(defun abfify-region-or-buffer ()
  "Abfify the region if it is active. Otherwise, abfify the buffer"
  (interactive)
  (if (region-active-p)
      (abfify-region-kernel (region-beginning) (region-end) "--no-indent" "--no-skip")
    (abfify-buffer)))

;;;###autoload
(define-minor-mode abf-mode
  "Automatically run ABF before saving."
  :lighter " ABF"
  (if abf-mode
      (add-hook 'before-save-hook 'abfify-buffer nil t)
    (remove-hook 'before-save-hook 'abfify-buffer t)))

(provide 'abfify)

;;; abfify.el ends here
