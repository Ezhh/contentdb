// @author rubenwardy
// @license magnet:?xt=urn:btih:1f739d935676111cfff4b4693e3816e664797050&dn=gpl-3.0.txt GPL-v3-or-Later

$(function() {
	function finish() {
		$(".pkg_wiz_1").hide()
		$(".pkg_wiz_2").hide()
		$(".pkg_repo").show()
		$(".pkg_meta").show()
	}

	function repoIsSupported(url) {
		try {
			return URI(url).hostname() == "github.com"
		} catch(e) {
			return false
		}
	}

	$(".pkg_meta").hide()
	$(".pkg_wiz_1").show()
	$("#pkg_wiz_1_next").click(function() {
		const repoURL = $("#repo").val();
		if (repoIsSupported(repoURL)) {
			$(".pkg_wiz_1").hide()
			$(".pkg_wiz_2").show()
			$(".pkg_repo").hide()

			performTask("/tasks/getmeta/new/?url=" + encodeURI(repoURL)).then(function(result) {
				$("#name").val(result.name || "")
				$("#title").val(result.title || "")
				$("#repo").val(result.repo || repoURL)
				$("#issueTracker").val(result.issueTracker || "")
				$("#desc").val(result.description || "")
				$("#shortDesc").val(result.short_description || "")
				if (result.forumId) {
					$("#forums").val(result.forumId)
				}
				finish()
			}).catch(function(e) {
				alert(e)
				$(".pkg_wiz_1").show()
				$(".pkg_wiz_2").hide()
				$(".pkg_repo").show()
				// finish()
			})
		} else {
			finish()
		}
	})
})
