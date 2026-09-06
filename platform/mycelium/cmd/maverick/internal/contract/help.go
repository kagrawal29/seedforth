package contract

import (
	"github.com/Qubit-Capital/maverick/cmd/maverick/internal/help"
)

// HelpText returns the help text that is tested against the golden file.
func HelpText() string {
	return help.Text()
}
