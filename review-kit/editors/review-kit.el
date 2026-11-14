;;; review-kit.el --- Run the review-kit checks from Emacs  -*- lexical-binding: t; -*-

;;; Commentary:
;; Load this file, set `review-kit-home' (or the REVIEWKIT_HOME environment
;; variable), then use M-x review-kit-gate and the other commands.  Output
;; goes to a compilation buffer, so `next-error' jumps to each "file:line".

;;; Code:

(require 'compile)

(defgroup review-kit nil
  "Pre-commit and pre-push checks."
  :group 'tools)

(defcustom review-kit-home (getenv "REVIEWKIT_HOME")
  "Directory that holds the review-kit scripts/ directory."
  :type '(choice (const :tag "Unset" nil) directory))

(defun review-kit--run (script &rest args)
  "Run SCRIPT from the kit with ARGS at the root of the current repository."
  (unless (and review-kit-home
               (file-exists-p (expand-file-name "scripts/gate.py" review-kit-home)))
    (user-error "Set `review-kit-home' to the review-kit directory"))
  (let ((root (locate-dominating-file default-directory ".git")))
    (unless root
      (user-error "Not inside a git repository"))
    (let ((default-directory root))
      (compile (mapconcat #'shell-quote-argument
                          (append (list "python3"
                                        (expand-file-name (concat "scripts/" script)
                                                          review-kit-home))
                                  args)
                          " ")))))

;;;###autoload
(defun review-kit-sweep-staged ()
  "Run the code-quality sweep on the staged changes."
  (interactive)
  (review-kit--run "cq_sweep.py" "--staged"))

;;;###autoload
(defun review-kit-sweep-commit ()
  "Run the code-quality sweep on the last commit."
  (interactive)
  (review-kit--run "cq_sweep.py" "--commit" "HEAD"))

;;;###autoload
(defun review-kit-truth-audit ()
  "Run the truth audit on the last commit."
  (interactive)
  (review-kit--run "truth_audit.py" "HEAD"))

;;;###autoload
(defun review-kit-stack-churn ()
  "List lines a commit removes that an earlier commit of the stack added."
  (interactive)
  (review-kit--run "stack_churn.py"))

;;;###autoload
(defun review-kit-local-review ()
  "Run the configured AI reviewer on each commit of the stack."
  (interactive)
  (review-kit--run "local_review.py"))

;;;###autoload
(defun review-kit-gate ()
  "Run the pre-push gate on the stack."
  (interactive)
  (review-kit--run "gate.py"))

(provide 'review-kit)
;;; review-kit.el ends here
