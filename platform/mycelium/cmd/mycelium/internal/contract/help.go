package contract

import (
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/help"
)

// HelpText returns the help text that is tested against the golden file.
func HelpText() string {
	return help.Text()
}
