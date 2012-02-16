jQuery(document).ready(function () {
    var ADs_css_top, ADs_height, footer_y, sidebar_bottom_y;

    setTimeout(function () {
        $("#right-col-ad").slideDown(2000, function () {
            ADs_css_top = $("#right-col-ad").css("top");
            ADs_height = $("#right-col-ad").height();
            footer_y = $("#end-of-content").offset().top;
            sidebar_bottom_y = $("#bottom_most_of_right_col").offset().top;
            $(window).scroll();
        });
    }, 1000);

    $(window).scroll(function () {
        var dsoctop = $(window).scrollTop();

        if (dsoctop > sidebar_bottom_y) {
            if ($("#right-col-ad").css("position") == "static") {
                $("#right-col-ad").fadeOut(0);
                $("#right-col-ad").css("top", "6px");
                $("#right-col-ad").css("position", "fixed");
                $("#right-col-ad").fadeIn(1500);
            }
            else {
                if (dsoctop > footer_y - ADs_height && $("#ad-side-big-2").css("display") != "none") {
                    $("#ad-side-big-2").fadeOut(800);
                }
                else if (dsoctop < footer_y - ADs_height && $("#ad-side-big-2").css("display") == "none") {
                    $("#ad-side-big-2").fadeIn(800);
                }
            }
        }
        else if (dsoctop < sidebar_bottom_y - ADs_height && $("#right-col-ad").css("position") == "fixed") {
            $("#right-col-ad").fadeOut(0);
            $("#right-col-ad").css("top", top);
            $("#right-col-ad").css("position", "static");
            $("#right-col-ad").fadeIn(1500);
        }
    });
});