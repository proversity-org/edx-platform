define([
    'jquery', 'js/collections/asset', 'js/views/assets', 'jquery.fileupload'
], function($, AssetCollection, AssetsView) {
    'use strict';
    return function(config) {
        var assets = new AssetCollection(),
            assetsView;

        assets.url = config.assetCallbackUrl;
        assets.urlRoot = config.assetCallbackUrl;
        if(config.filterCriteria && config.filterCriteria.trim().length > 0){
            var regex = /[?&]?([^=]+)=([^&]*)/g; //regex to test for query parameters in url
            var urlConcatChar = (regex.exec(config.assetCallbackUrl) != null) ? '&' : urlConcatChar = '?';
            assets.url = config.assetCallbackUrl+urlConcatChar+'filter_criteria='+config.filterCriteria;
        }

        assetsView = new AssetsView({
            collection: assets,
            el: $('.wrapper-assets'),
            uploadChunkSizeInMBs: config.uploadChunkSizeInMBs,
            maxFileSizeInMBs: config.maxFileSizeInMBs,
            maxFileSizeRedirectUrl: config.maxFileSizeRedirectUrl
        });

        assetsView.render();
    };
});
