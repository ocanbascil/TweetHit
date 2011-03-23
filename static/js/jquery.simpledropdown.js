/*
Name: jQuery Simple Drop Down Plugin
Author: Etienne Fardet
Version: 1.2
*/

(function($){  
 $.simpledropdown = function(selector) {
	 
		$(selector).children("ul").addClass("dropdown");
		$("ul.dropdown>li:first-child").addClass("dropselected");
		$("ul.dropdown>li").not(".dropdown>li:first-child").addClass("drop");		

		$("ul.dropdown").click(function() {
			var subitems = $(this).find(".drop li");
			var selecteditem = $(this).find(".dropselected");
			subitems.slideToggle("fast", function() {
				
			subitems.click(function() {
				var selection = $(this).text();
				selecteditem.text(selection).fadeOut(5, function() {
					if (jQuery.browser.msie) {
						$(this).fadeIn(100);
					} else {
						$(this).fadeIn(400);
					}
				});
			});
		});
	return false;
	});
 };  
})(jQuery); 
