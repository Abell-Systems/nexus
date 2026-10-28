# Unmerged work held only locally: backup register

**Status:** Maintenance record of the repository. It is **not** part of any acceptance record or scientific protocol, and it decides nothing about the content it lists. It carries no private paths and no data.
**Date:** 2026-10-28

## 1. docs/ceimar-article-charts (pull request #103)

| Item | State |
|---|---|
| What the local branch holds beyond what was merged | 8 commits, 2026-09-23 to 2026-09-25: data and notes of the article and thesis work with Minesoft Origin (an ID list of about 20,000 lines, scope decision, README of the experiment) and the pre-registration design and implementation plan of the dense-exclusive stratified sample |
| Where else these commits exist | Nowhere known. The remote branch ends at `4d2e22a` (one earlier commit); the local branch ends at `696c692` |
| Backup | One git bundle of the branch, saved on 2026-10-28 in a private directory of the maintainer's machine. SHA-256 `cc87a5319ef5f9fceee8573dfca105f6a85c131843eb4a47bc4de37218b0179c`; tip `696c692290ac7abb5e87fbed948f5e5349387bd3` |
| Verified | The bundle verifies as a complete history; it was cloned into a temporary directory, the tip was recovered, and three files were compared byte for byte with the branch (the ID list, the scope decision, the design of the pre-registration) |
| Independence | **None.** The bundle and the branch are on the same disk as the repository (the virtual disk of WSL, one filesystem). A copy on the Windows drive mounted in WSL is probably the same physical disk and is **not** counted as a second copy |
| Pushed | No. Part of the content is Minesoft data whose licence for publication is the owner's decision |
| Open | A second copy on an independent volume (external disk or private remote storage under the owner's control), verified by hash, by cloning the copy, by the tip `696c692` and by the three files above. Until then the task is open and the bundle is the **only** backup |

Rules while it is open: do not modify, move or delete the local branch, the bundle or the related worktrees.

## 2. How to add an entry

One section per branch or set of files: what it holds, where it exists, backup and its hash, what was verified, independence of the copy, whether it was pushed and why, what is open. Do not write private paths, credentials or data here.
