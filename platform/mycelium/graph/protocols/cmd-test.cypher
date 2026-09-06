// @node_id: protocol-cmd-test
// @label: Test Command
// @kind: command
// @description: List active test cases with their results

// Atom 1: Count active tests by result
MATCH (t:TestCase) WHERE coalesce(t.enabled, true) = true
WITH t.last_result AS result, count(t) AS count
RETURN 'test-summary|' + result + '|' + toString(count) AS output
ORDER BY result;

// Atom 2: List all active tests with status
MATCH (t:TestCase) WHERE coalesce(t.enabled, true) = true
RETURN 'test-item|' + coalesce(t.last_result, '?') + '|' + t.node_id + '|' + coalesce(t.label, '(unlabeled)') AS output
ORDER BY t.node_id;
