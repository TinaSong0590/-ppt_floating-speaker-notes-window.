-- Optional helper: when focus is on the overlay, you can bind a shortcut
-- that also sends Right Arrow to WPS so both stay in sync.
-- Usage: osascript scripts/send_page_to_wps.applescript next
--        osascript scripts/send_page_to_wps.applescript prev

on run argv
	set direction to "next"
	if (count of argv) ≥ 1 then set direction to item 1 of argv
	set keyCode to 124 -- right
	if direction is "prev" then set keyCode to 123 -- left

	tell application "System Events"
		set targetProc to missing value
		repeat with procName in {"wpsoffice", "WPS Office"}
			if exists process procName then
				set targetProc to process procName
				exit repeat
			end if
		end repeat
		if targetProc is missing value then error "WPS 未运行"
		tell targetProc
			set frontmost to true
			key code keyCode
		end tell
	end tell
end run
