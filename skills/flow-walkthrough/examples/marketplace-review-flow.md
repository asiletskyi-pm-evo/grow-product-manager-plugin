# Reference walk — leave a product review (marketplace buyer app, iPhone app on a Mac)

Measured 2026-09-10 on Claude Cowork, driver level `foreground`, account `own`, write boundary `stop-before-irreversible`. Product: "Product 1" (a marketplace buyer app installed from the Mac App Store on Apple Silicon).

## Expected steps

| # | Intent | Action | Observed | Status |
|---|--------|--------|----------|--------|
| 1 | Find a product | search "sneakers", Enter | results list | ok |
| 2 | Open a product with reviews | tap a card | product page | ok |
| 3 | Find where to write a review | scroll to the reviews block | "Ask a question" button only, no "Write a review" | friction |
| 4 | Try the reviews list | tap "All" | rating breakdown + list, still no write entry | friction |
| 5 | Open the account area | overflow arrow → Account | account screen | friction (hidden tab) |
| 6 | Open the reviews hub | tap "Reviews" | tabs, filter "Awaiting rating", items with "Add review" | ok |
| 7 | Open the review form | tap "Add review" | photo, title, text, pros, cons — no star rating | friction |
| 8 | Fill title and text | type | text visible | ok |
| 9 | Reach the submit button | scroll | "Publish review" visible | blocked: write boundary |
| 10 | Close the form | tap X | modal "Rate the product?" with stars and Publish; typed text would auto-publish on rating | friction |
| 11 | Cancel and reopen | Cancel → Add review | form empty — draft lost | friction |
| 12 | Orders filter | Orders → filter "Awaiting review" | empty state "your order history is empty" while the hub lists two items | friction |

## Expected frictions

- major, N5 error prevention — the rating lives only in the exit modal; a rating there publishes the typed text (step 10)
- major, N3 user control — the draft is lost silently on close (step 11)
- major, N4 consistency — the orders filter and the reviews hub disagree; the empty-state copy is wrong (step 12)
- minor, N6 recognition — no review entry point on the product page or the reviews list (steps 3–4)
- minor, N6 recognition — the account tab sits behind an overflow arrow (step 5)
- cosmetic, N1 visibility — the exit modal appears even for an empty form (step 11)

## Driver facts learned

- background window capture fails for iPhone apps on a Mac → foreground only
- a grammar-checker overlay blocked clicks until it was quit
- wheel scroll and drag-swipe both work; typing without a focused field is lost
- the batch tool's save-to-disk did not surface paths → save screenshots with `screencapture` and read them back
- window-scoped `screencapture -x -l <window id>` works for these apps (2026-09-11): the pack holds only the app window, and the part hidden under the Dock is rendered
- re-run through the skill (2026-09-11, 9 steps, verdict blocked_at:7): the six frictions reproduced; the "All" link in the reviews block did not respond to two taps that day
